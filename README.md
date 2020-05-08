# About
This repository contains two things:
- Examples of external services structure to be compatible with Teanga-backend
- The internal services structure used by teanga-backend services (currently the only internal service is called request_manager)
# Guidelies how to create services 
## Essential Requirements
### Docker
#### runs a webserver when started
#### webserver port must be configurable, using PORT enviroment variable
#### webserver Openapi-specification .yaml file can be acessed at /openapi.yaml
#### Docker image is expected to be pulled from dockerhub, so it's necessary to upload the image in a public dockerhub repository
#### Example
```
FROM ubuntu:latest
USER root
RUN apt-get update
RUN apt-get install -y python-pip python-dev build-essential
RUN apt-get install -y python3-pip python3-dev

WORKDIR /app
copy ./r.txt r.txt
RUN pip3 install -r r.txt
copy ./ /app
RUN chmod +x /app
RUN mkdir /app/output

copy ./openapi.yaml /openapi.yaml
CMD ["sh","-c","/app/webserver.sh ${PORT}"]
```
### OpenApi-specification
#### follow  [open-api specifications][https://www.openapis.org/about] to describe api. good documentation can be found at [swagger documentation][https://swagger.io/docs/specification/about/]
#### Inputs and Outputs must follow both [json-ld][https://json-ld.org/] and open-api specifications 
#### Unamed inputs and outputs should be avoided
### Example
```
openapi: "3.0.0"
info:
  version: 1.0.0
  title: Vocabulary API
servers:
    - url: http://localhost:8000
paths:
  /vocabulary/{language}/top/{number_of_words}:
    get:
      summary: List all words
      operationId: list_top_k
      parameters:
        - name: language
          in: path
          description: language of the vocabulary
          required: true
          schema:
            type: string
            enum: ["en","sp","ge"]
        - name: number_of_words
          in: path
          description: How many top words return at one time (max 100)
          required: true 
          schema:
            type: integer
            format: int32
      responses:
        '200':
          description: A paged array of words
          content:
            application/json:    
              schema:
                $ref: "#/components/schemas/Words"
  /wordembeddings/{number_of_dimensions}:
    post:
      summary: calculate word embeddings for each sentence in as list of sentences
      operationId: calculate_word_embeddings 
      parameters:
        - name: number_of_dimensions
          in: path
          description: How many dim in the wordembeddings
          required: true 
          schema:
            type: integer
            format: int32
      requestBody:
          required: true
          content:
              application/json:
                schema:
                    $ref: "#/components/schemas/Words"
      responses:
        '200':
          description: word embbedings foreach word of a list of words 
          content:
            application/json:    
              schema:
                $ref: "#/components/schemas/Embeddings"
components:
  schemas:
    Words:
      type: array 
      items:
          type: string
    Embeddings:
      type: array
      items:
          type: array
          items:
            type: float
```
