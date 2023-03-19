# Import the necessary libraries
import logging
import os
import re
import uuid

import validators
from flask import Flask, request, render_template
from markupsafe import Markup
from pyshex import ShExEvaluator
from pyshex.utils.sparql_query import SPARQLQuery
from sparqlslurper import SlurpyGraphWithAgent

import playground.shexviz_test

# Create a Flask application
app = Flask(__name__)

# Set up logging for the application
logging.basicConfig(level=logging.DEBUG)


# Define a function to validate a ShEx shape against a SPARQL query
def process_html(content):
    for key in content:
        for index, line in enumerate(content[key]):
            # Define the regex pattern to match URLs
            url_pattern = re.compile(r'(https?://\S+)')
            # Replace each matched URL with an HTML link
            formatted_text = url_pattern.sub(r'<a href="\1">\1</a>', line)
            content[key][index] = Markup("<li>" + formatted_text + "</li>")
    return content


def validate(endpoint, shex, sparql):
    # If the SPARQL query includes 'select ?item'
    if "select ?item " in sparql.lower():
        content = {"PASS": [], "FAIL": [], "ERROR": []}
        # Get the focus nodes from the SPARQL query
        try:
            nodes = SPARQLQuery(endpoint, sparql).focus_nodes()
        except Exception as e:
            content["ERROR"] = ["QUERY EXECUTION FAILED\n" + str(e)]
            return content
        # For each focus node
        for node in nodes:
            # Evaluate the ShEx shape against the node
            result = ShExEvaluator(SlurpyGraphWithAgent(endpoint), shex, node).evaluate()
            # For each result of the evaluation
            for r in result:
                # If the result is not successful
                if not r.result:
                    content["FAIL"].append(f"{r.focus}: {r.reason}")
                # If the result is successful
                else:
                    content["PASS"].append(f"{r.focus}")
    # If the SPARQL query does not include 'select ?item'
    else:
        content = {"ERROR": "No 'select ?item' in SPARQL query please fix it..."}
    content = process_html(content)
    return content


# Define a route for the Flask application
@app.route('/', methods=['GET', 'POST'])
def home():
    # If the request method is POST
    if request.method == 'POST':
        # Get the ShEx, SPARQL, and endpoint values from the form
        text_shex = request.form['shex']
        text_sparql = request.form['sparql']
        # Obtain the endpoints list
        endpoints = sorted(list(set([endpoint.strip() for endpoint in open("./storage/endpoints.txt").readlines()])))
        shex_examples = {}
        for filename in os.listdir("./static/shapes/"):
            content = open("./static/shapes/" + filename).read()
            shex_examples[filename] = content
        print(">>>", shex_examples)
        # Obtain user input and drop downmenu from endpoints
        endpoint = request.form['endpoint']
        endpoint_menu = request.form['endpoint_menu']

        if request.form['submit_type'] == "shex2dot":
            # dotschema = shex2dot.shex2dot(request.form['shex'])
            # print(dotschema)
            uuid_path = "./storage/generated/" + str(uuid.uuid4())
            svg_data = playground.shexviz_test.main(shex=request.form['shex'], path=uuid_path)

            # TODO REMOVE FILE
            return render_template('index.html',
                                   text_output_fail=[],
                                   text_output_pass=[],
                                   endpoint=endpoint,
                                   text_shex=text_shex,
                                   text_sparql=text_sparql,
                                   endpoint_menu=endpoints,
                                   shex_menu=shex_examples,
                                   shex_image=svg_data
                                   )

        if request.form['submit_type'] == "validate":
            # If user input valid urls
            if validators.url(endpoint):
                # Validate the ShEx shape against the SPARQL query using the endpoint
                text_output = validate(endpoint, text_shex, text_sparql)
            # If menu valid url
            elif validators.url(endpoint_menu):
                # Validate the ShEx shape against the SPARQL query using the endpoint
                try:
                    text_output = validate(endpoint_menu, text_shex, text_sparql)
                except ValueError as e:
                    text_output = {"FAIL": [], "PASS": [], "ERROR": [e]}
            else:
                print("No can do...")
                text_output = {"FAIL": [], "PASS": [], "ERROR": ["NO ENDPOINT SELECTED"]}
                # Return results
                print("ENDPOINTS: ", endpoints)
                return render_template('index.html',
                                       text_output_fail=text_output["FAIL"],
                                       text_output_pass=text_output["PASS"],
                                       text_output_error=text_output["ERROR"],
                                       endpoint=endpoint,
                                       text_shex=text_shex,
                                       text_sparql=text_sparql,
                                       endpoint_menu=endpoints,
                                       shex_menu=shex_examples,
                                       )

            if len(text_output["ERROR"]) == 0:
                # ENDPOINT SHOULD BE OK... ADD USER ENDPOINT TO LIST
                with open("./storage/endpoints.txt", "a") as output:
                    if validators.url(endpoint):
                        output.write("\n" + endpoint + "\n")

            # Return results
            return render_template('index.html',
                                   text_output_fail=text_output["FAIL"],
                                   text_output_pass=text_output["PASS"],
                                   text_output_error=text_output["ERROR"],
                                   endpoint=endpoint,
                                   text_shex=text_shex,
                                   text_sparql=text_sparql,
                                   endpoint_menu=endpoints,
                                   shex_menu=shex_examples,
                                   )
        elif request.form['submit_type'] == "example":
            shex_menu = request.form['shex_menu']
            print("shex_menu", len(shex_menu))
            return render_template('index.html',
                                   # text_output_fail=text_output["FAIL"],
                                   # text_output_pass=text_output["PASS"],
                                   # text_output_error=text_output["ERROR"],
                                   endpoint=endpoint,
                                   text_shex=shex_menu,
                                   text_sparql=text_sparql,
                                   endpoint_menu=endpoints,
                                   shex_menu=shex_examples,
                                   )
        else:
            print("New type detected!")

    # If the request method is not POST
    else:
        print("ELSE!!!!")
        # Set the default endpoint, ShEx shape, and SPARQL query
        endpoint = "https://query.wikidata.org/sparql"
        endpoints = sorted(list(set([endpoint.strip() for endpoint in open("./storage/endpoints.txt").readlines()])))
        shex_examples = {}
        for filename in sorted(os.listdir("./static/shapes/")):
            content = open("./static/shapes/" + filename).read()
            shex_examples[filename] = content

        text_shex = open("./static/shapes/" + os.listdir("./static/shapes")[0]).read()
        text_sparql = open("./static/sparql/query1.sparql").read()

        # Render the template with the output, endpoint, ShEx shape, and SPARQL query
        return render_template('index.html',
                               text_output_fail=[],
                               text_output_pass=[],
                               endpoint=endpoint,
                               text_shex=text_shex,
                               text_sparql=text_sparql,
                               endpoint_menu=endpoints,
                               shex_menu=shex_examples,
                               )


# Run the Flask application
if __name__ == '__main__':
    app.run()
