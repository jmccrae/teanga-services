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

    """
    createClient_cmd = shlex.split(f'./create_client.sh {serviceOAS_absPath} {service_id}')
    subprocess.call(createClient_cmd) 
    os.chdir(serviceClient_pkgFolder)
    pip.main(["install","."])
    os.chdir(base_folder)
    """
    client = importlib.import_module("client_"+service_id)
    return client 

def check_union(expected_inputs, dependencies_outputs, dependencies_inputs):
    matches  = [parameter_name  
                    for parameter_name in expected_inputs
                        if((parameter_name in dependencies_inputs) \
                                or (parameter_name in dependencies_inputs))] 

    if len(matches) == len(expected_inputs):
        status = "validated"
    else:
        status = "not_validated"
    return status


def operationId_to_endpoint(OAS_paths):
    map_operationId_to_endpoint = {}
    for url in OAS_paths.keys():
        for request_method in OAS_paths[url]:
            operationId = OAS_paths[url][request_method]["operationId"] 
            map_operationId_to_endpoint[operationId] = (url, request_method)
    return map_operationId_to_endpoint

def flatten_info(OAS):
    paths_info = [] 
    for url in OAS['paths'].keys():
        for request_method in OAS['paths'][url].keys():
            operation_data=OAS['paths'][url][request_method]
            print(operation_data.keys())
            parameters =  operation_data.get("parameters",[])
            sucess_response = operation_data["responses"]["200"]
    schemas = OAS['components']['schemas']
    return parameters, sucess_response, schemas 

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
