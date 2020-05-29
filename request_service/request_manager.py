from __future__ import print_function
import importlib
import time
import os
from collections import ChainMap

from os.path import join
from pprint import pprint
import subprocess
import shlex
import pip
import inspect
import requests
import datetime
import json
import yaml

def create_api_client(base_folder, OAS_folder, 
                      serviceOAS_absPath):
    service_id    = serviceOAS_absPath.split("/")[-1].replace(".yaml","")
    serviceClient_name = "client_"+service_id
    serviceClient_pkgFolder = os.path.join("/teanga/clients",
                                           serviceClient_name)

    createClient_cmd = shlex.split(f'./create_client.sh {serviceOAS_absPath} {service_id}')
    subprocess.call(createClient_cmd) 
    os.chdir(serviceClient_pkgFolder)
    pip.main(["install","."])
    os.chdir(base_folder)
    client = importlib.import_module("client_"+service_id)
    return client 


def flatten_info(OAS, operationId):
    flatten = {}
    for url in OAS['paths'].keys():
        for request_method in OAS['paths'][url].keys():
            operation_data=OAS['paths'][url][request_method]
            if operation_data["operationId"] == operationId:
                flatten["endpoint"] = url
                flatten["request_method"] = request_method
                flatten["parameters"] =  operation_data.get("parameters",[])
                flatten["requestBody"] =  operation_data.get("requestBody",{})
                flatten["sucess_response"] = operation_data["responses"]["200"]
                flatten["response_schemas"] = \
                        flatten["sucess_response"]['content']['application/json']['schema']\
                        if flatten["sucess_response"].get('content',False) else None
    flatten["schemas"] = OAS['components']['schemas']
    return flatten 

def match_input(currService_flattenedOAS, given_input, dependecies_inputs, dependecies_outputs):
    print(f"{'#'*4} Beginning of Matching") 
    service_input = {}
    named_candidates = ChainMap(given_input, *dependecies_outputs, *dependecies_inputs)
    schemas_candidates = ChainMap(*dependecies_outputs, *dependecies_inputs)
    missing_parameters = []
    for expected_parameter in currService_flattenedOAS["parameters"]:
        parameter_name = expected_parameter['name']
        value = named_candidates.get(parameter_name, False)
        if value == False: missing_parameters.append(parameter_name)
        else: 
            expected_schema = [d for d 
                    in currService_flattenedOAS["parameters"] 
                    if d["name"] == parameter_name ][0] 
            service_input[parameter_name] = {"value":value, "schema":expected_schema} 
    print(f'expected inputs: {[d["name"] for d in currService_flattenedOAS["parameters"]]}')
    print(f'User input: {given_input}')
    print(f'Dependencies INP: {dependecies_inputs}')
    print(f'Dependencies OUT: {dependecies_outputs}')
    print(f'Missing parameters after matching: {missing_parameters}')
    if currService_flattenedOAS["requestBody"]:
        print(f'expected requestBody: {currService_flattenedOAS["requestBody"]}')
        # if there is input files, put then in requestBody
        if len(given_input.get("files",[])) == 1:
            requestBody_value = open(join("files",given_input["files"][0])).read()
        elif len(given_input.get("files",[])) > 1: 
            raise Exception("sending multiple files still not implemented")
        # if there is no input files, check if expected requestBody schema matches with dpdcies
        else:
            expected_schema =  currService_flattenedOAS["requestBody"]\
                        ['content']['application/json']['schema']['$ref'].split("/")[-1]
            print([d dependecies_outputs)
            raise Exception("requestBody not defined")
        """
        #schema_name = currService_flattenedOAS["requestBody"]['content']['application/json']['schema']['$ref'].split("/")[-1]
        requestBody_value = schemas_candidates.get(schema_name, {"value":{}})
        expected_requestBody_schema = currService_flattenedOAS['schemas'][schema_name]
        service_input["request_body"] = requestBody_value
        schema_name = currService_flattenedOAS["response_schemas"]["$ref"].split("/")[-1]
        requestBody_value = currService_flattenedOAS["schemas"][schema_name]
        """

    # expected output info
    if currService_flattenedOAS.get("response_schemas",False):
        if currService_flattenedOAS["response_schemas"]["type"] == "array":
            expected_output_schema = {"name":  None,
                                      "schema": currService_flattenedOAS["response_schemas"]
                                     }  
        else:
            expOut_name = currService_flattenedOAS["response_schemas"]["$ref"].split("/")[-1]
            expected_output_schema = {"name":expOut_name,
                                      "schema":currService_flattenedOAS["schemas"][expOut_name]}  
    else:
        expected_output_schema = None

    print(f"{'#'*4} End of Matching ") 
    return service_input, expected_output_schema 

def setup_request(named_inputs,
                endpoint,
                request_method,
                host_port):
    print(f"{'#'*4} Beginning of preparing request") 
    remaining_inputs = named_inputs.copy()
    for name, value in named_inputs.items():
        if f'{{{name}}}' in endpoint:
            endpoint = endpoint.replace(f'{{{name}}}',str(value))
            remaining_inputs.pop(name,None);
    url = f'http://localhost:{host_port}{endpoint}'
    if "request_body" in remaining_inputs.keys():
        data =  remaining_inputs.pop("request_body",None)
        request_ = requests.Request(
                      method=request_method.upper(),
                      url=url,
                      params=remaining_inputs,
                      data=data)
    else:
        request_ = requests.Request(
                method=request_method.upper(),
                params=remaining_inputs,
                      url=url)
    request_ = request_.prepare()
    print(f'all given inputs : {named_inputs}')
    print(f'Remaining inputs : {remaining_inputs}')    
    print(f'final url: {request_.url}')    

    print(f"{'#'*4} End of preparing request") 
    return request_ 

def execute_api_client(servicesOAS,
                       workflow_idx, workflow):
    session = requests.Session()
    currService_workflow = workflow[workflow_idx]
    print(f'{"-"*13} STEP {workflow_idx}:{currService_workflow["operation_id"]} {"-"*13}')
    currService_OAS = servicesOAS[workflow_idx]
    dependecies_OAS = [flatten_info(servicesOAS[workflow_idx]['OAS'], workflow_idx)
                        for workfolow_idx in currService_workflow['dependencies']]  
    dependecies_inputs = [workflow[workflow_idx]["input"]
                        for workflow_idx in currService_workflow['dependencies']]  
    dependecies_outputs = [{workflow[workflow_idx]["output"]["schema"]["name"]:workflow[workflow_idx]["output"]}
                        for workflow_idx in currService_workflow['dependencies']
                        if workflow[workflow_idx]["output"]["schema"] != None]  

    currService_flattenedOAS= flatten_info(currService_OAS['OAS'], currService_workflow["operation_id"])
    given_input = currService_workflow.get("input",{})
    service_input, expected_output_schema =\
            match_input(currService_flattenedOAS, given_input, dependecies_inputs, dependecies_outputs) 
    service_name_val = {name:d["value"] for (name,d) in service_input.items()}
    request_ = setup_request(service_name_val,
                currService_flattenedOAS["endpoint"],
                currService_flattenedOAS["request_method"],
                currService_workflow["host_port"])


    api_response = session.send(request_).text
    if expected_output_schema != None: 
        api_response= eval(session.send(request_).text)
        response_dict = json.dumps(api_response)
    else:
        response_dict = api_response
    workflow[workflow_idx]["input"] = service_input
    workflow[workflow_idx]["output"] =\
                            {"value":response_dict,
                             "schema":expected_output_schema}
    print(f'final output: {workflow[workflow_idx]["output"]}')
    print(f'{"-"*13} END OF  STEP {workflow_idx}:{currService_workflow["operation_id"]} {"-"*13}')
    i=input()
    if i =="1":
        exit()
    return workflow

if __name__ == "__main__":
    today_date = datetime.datetime.now().strftime("%d%m%Y")
    base_folder=os.path.dirname(os.path.abspath(__file__))
    OAS_folder=os.path.join(base_folder,"OAS")
    os.chdir(base_folder) 
    workflow_file = os.path.join(base_folder,"workflows",f'updated_dev_naisc_workflow_{today_date}.json')

    workflow = json.load(open(workflow_file))
    OAS_specifications = {fn.split("_")[0]:
                            {
                                "filepath":os.path.join(OAS_folder,fn),
                                "OAS":yaml.load(open(os.path.join(OAS_folder,fn))),
                            }
                            for fn in sorted(os.listdir(OAS_folder))
                         }

    for (workflow_idx, serviceOAS) in OAS_specifications.items():
        #client = create_api_client(
        #            base_folder, OAS_folder, serviceOAS["filepath"],
        #        )
        workflow = execute_api_client(OAS_specifications,
                                      workflow_idx, workflow)
    with open("./IO/IO.json","w") as IO_file: 
        IO_file.write(json.dumps(workflow))

