from __future__ import print_function
import importlib
import time
import os
from collections import ChainMap

from pprint import pprint
import subprocess
import shlex
import pip
import inspect

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
                flatten["parameters"] =  operation_data.get("parameters",[])
                flatten["requestBody"] =  operation_data.get("requestBody",{})
                flatten["sucess_response"] = operation_data["responses"]["200"]
                flatten["response_schemas"] = flatten["sucess_response"]['content']['application/json']['schema']
    flatten["schemas"] = OAS['components']['schemas']
    return flatten 

def match_input(currService_flattenedOAS, given_input, dependecies_inputs, dependecies_outputs):
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

    if currService_flattenedOAS["requestBody"]:
        schema_name = currService_flattenedOAS["requestBody"]['content']['application/json']['schema']['$ref'].split("/")[-1]
        requestBody_value = schemas_candidates.get(schema_name, {"value":{}})
        expected_requestBody_schema = currService_flattenedOAS['schemas'][schema_name]
        service_input["request_body"] = requestBody_value
    schema_name = currService_flattenedOAS["response_schemas"]["$ref"].split("/")[-1]
    requestBody_value = currService_flattenedOAS["schemas"][schema_name]
    expected_output_schema = {"name":schema_name,"schema":schema}  
    return service_input, expected_output_schema 

def execute_api_client(client,       servicesOAS,
                       workflow_idx, workflow):
    workflow_data = workflow[workflow_idx]
    description_data = servicesOAS[workflow_idx]
    dependecies_OAS = [servicesOAS[workflow_idx]  
    opId_to_endpoint = operationId_to_endpoint(description_data['OAS']['paths'])
    expected_inputs, expected_response, schemas = flatten_info(description_data['OAS'])

    expected_inputs = description_data['OAS']
    service_input = workflow_data.get("input",{})
    with client.ApiClient() as api_client:
        api_instance = client.DefaultApi(api_client)
        api_method = getattr(api_instance,
                        workflow_data["operation_id"])
        if "request_body" in inspect.getargspec(api_method)[0]:
            request_body = {"request_body":service_input}
            service_input = request_body
        api_response= api_method(**service_input)
        response_dict = json.dumps(api_response)
        workflow[workflow_idx]["input"] = service_input
        workflow[workflow_idx]["output"] = eval(response_dict)
        return workflow

if __name__ == "__main__":
    try:
        base_folder=os.path.dirname(os.path.abspath(__file__))
        OAS_folder=os.path.join(base_folder,"OAS")
        os.chdir(base_folder), 
        workflow_file = os.path.join(base_folder,"workflows","deploy_workflow.json")

        workflow = json.load(open(workflow_file))
        OAS_specifications = {fn.split("_")[0]:
                                {
                                    "filepath":os.path.join(OAS_folder,fn),
                                    "OAS":yaml.load(open(os.path.join(OAS_folder,fn))),
                                }
                                for fn in sorted(os.listdir(OAS_folder))
                             }

        for (workflow_idx, serviceOAS) in OAS_specifications.items():
            client = create_api_client(
                        base_folder, OAS_folder, serviceOAS["filepath"],
                     )
            workflow = execute_api_client(client, OAS_specifications,
                                          workflow_idx, workflow)
        with open("./IO/IO.json","w") as IO_file: 
            IO_file.write(json.dumps(workflow))

    except Exception as Error:
        with open("error_log","a+") as log:
            log.write(str(Error)+"\n")
