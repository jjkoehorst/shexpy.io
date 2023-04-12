import base64
import json
import os
import shutil
import logging
from types import NoneType

import ShExJSG
import validators
from ShExJSG.ShExJ import TripleConstraint, IRIREF
from graphviz import Digraph
from pyjsg.jsglib import JSGArray
from pyshex.utils.schema_loader import SchemaLoader

# Set up logging for the application
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s', level=logging.DEBUG)

# Placeholder for URL prefixes
prefix_map = {
    # "http://www.w3.org/1999/02/22-rdf-syntax-ns#":"rdf",
    # "http://www.w3.org/2001/XMLSchema#": "xsd",
    # "http://www.w3.org/2000/01/rdf-schema#":"rdfs",
    # "http://www.w3.org/ns/shex#" : "shex",
}
shex_code: str = ""

# Create a new node and edge dict container
node_dict = {}
edge_dict = {}

# helper function to replace URL prefixes with their abbreviations
def url_fix(url):
    if validators.url(str(url)):
        url = str(url)
    if type(url) != str and not validators.url(str(url)):
        # print("Not a url string: ", url)
        return url
    if not validators.url(url):
        return url
    for key in prefix_map:
        if url.startswith(key):
            # replace the URL with its corresponding prefix
            return url.replace(key, prefix_map[key] + ":")
    return url


def escape_dot_string(s):
    """
    Escapes special characters in a string so that it can be used as a label in Graphviz.
    """
    # print(s)
    s = s.replace('\\', '\\\\')  # Escape backslashes first
    s = s.replace('"', '\\"')  # Escape double quotes
    s = s.replace('<', '\\<')  # Escape angle brackets
    s = s.replace('>', '\\>')
    s = s.replace('[', '\\[')
    s = s.replace(']', '\\]')
    s = s.replace('-', '\\-')
    s = s.replace('+', '\\+')
    s = s.replace('{', '\\{')
    s = s.replace('}', '\\}')
    s = s.replace('|', '\\|')
    s = s.replace(':', ';')
    return s


# main function to generate the UML diagram
def node_constraint(shape, identifier):
    global node_dict
    predicate = url_fix(shape["expression"]["predicate"])
    values = set()
    if "values" in shape["expression"]["valueExpr"]:
        for value in shape["expression"]["valueExpr"]["values"]:
            if 'value' in value:
                value = url_fix(value['value'])
            else:
                value = url_fix(value)
        values.add(value)
        node_dict[identifier][predicate] = "|".join(values)
    elif "pattern" in shape["expression"]["valueExpr"]:
        node_dict[identifier][predicate] = shape["expression"]["valueExpr"]["pattern"]


def get_values(values_expression):
    values = set()
    for value in values_expression:  # valueExpr["values"]:
        # Not sure if we need to fix the url
        if type(value) == dict and 'value' in value:
            value = url_fix(value['value'])
        elif type(value) == str:
            value = url_fix(value)
        elif type(value) == IRIREF:
            value = url_fix(str(value))
        elif type(value) == ShExJSG.ShExJ.ObjectLiteral:
            value = value.value
        elif type(value) == ShExJSG.ShExJ.NodeConstraint:
            print("TODO... working on NodeConstraint")
            value = ""
        else:
            logging.debug("Something else? " + str(type(value)))
            value = ""
        values.add(value.strip())
    values = list(values)
    if len(values) > 5:
        new_values = []
        for index, value in enumerate(values):
            if index % 5 == 0:
                new_values.append("\n")
            new_values.append(value)
        values = new_values
    return values


def triple_constraint(expression, identifier):
    global node_dict
    global edge_dict
    predicate = url_fix(expression.predicate)
    if predicate == '':
        predicate = '???'
    cardinality = "1"
    if "valueExpr" in expression:
        if expression.min:
            cardinality = str(expression.min)
        if expression.max:
            if expression.max == -1:
                cardinality = "*"
            else:
                cardinality += ":" + str(expression.max)

        # Draw a connection!
        if type(expression.valueExpr) == ShExJSG.ShExJ.NodeConstraint:
            if expression.valueExpr.values is not None:
                # print(">>>", expression.valueExpr.values)
                values = get_values(expression.valueExpr.values)
                node_dict[identifier][predicate] = "[" + "|".join(values) + "] (" + cardinality + ")"
                node_dict[identifier][predicate] = node_dict[identifier][predicate].replace("\n|", "\n")
            elif type(expression.valueExpr.datatype) == IRIREF:
                node_dict[identifier][predicate] = url_fix(
                    str(expression.valueExpr.datatype)) + " (" + cardinality + ")"
            elif expression.valueExpr.pattern is not None:
                node_dict[identifier][predicate] = str(expression.valueExpr.pattern) + " (" + cardinality + ")"
            elif type(expression) == TripleConstraint:
                if expression.valueExpr.nodeKind != None:
                    node_dict[identifier][predicate] = str(expression.valueExpr.nodeKind) + " (" + cardinality + ")"
                else:
                    node_dict[identifier][predicate] = "???" + " (" + cardinality + ")"
            else:
                logging.error("NOT CAPTURED")
        elif type(expression.valueExpr) == IRIREF:
            left = identifier
            right = url_fix(expression['valueExpr'])

            if left + "###" + right not in edge_dict:
                edge_dict[left + "#$#" + right] = []

            edge_dict[left + "#$#" + right].append(predicate)
        elif type(expression['valueExpr']) == ShExJSG.ShExJ.Shape:
            valueExpr = expression['valueExpr']
            if 'datatype' in valueExpr:
                node_dict[identifier][predicate] = url_fix(valueExpr['datatype']) + " (" + cardinality + ")"
                node_dict[identifier][predicate] = node_dict[identifier][predicate].replace("\n|", "\n")
            elif 'values' in valueExpr:
                values = get_values(valueExpr['values'])
                node_dict[identifier][predicate] = "[" + "|".join(values) + "] (" + cardinality + ")"
            elif 'expression' in valueExpr:
                if type(valueExpr.expression) == TripleConstraint:
                    triple_constraint(valueExpr.expression, identifier)
            else:
                logging.error("Need to capture something else...")
        elif type(expression.valueExpr) == ShExJSG.ShExJ.ShapeAnd:
            logging.error("TODO ShExJSG.ShExJ.ShapeAnd")
        elif type(expression.valueExpr) == ShExJSG.ShExJ.ShapeOr:
            # logging.debug("TODO ShExJSG.ShExJ.ShapeOr")
            values = get_values(expression.valueExpr.shapeExprs)
            node_dict[identifier][predicate] = "[" + "|".join(values) + "] (OR)"
        elif type(expression.valueExpr) == ShExJSG.ShExJ.ShapeNot:
            logging.error("TODO ShExJSG.ShExJ.ShapeNot")
        elif type(expression.valueExpr) == ShExJSG.ShExJ.ShapeDecl:
            logging.error("TODO ShExJSG.ShExJ.ShapeDecl")
        elif type(expression.valueExpr) == ShExJSG.ShExJ.ShapeExternal:
            logging.error("TODO ShExJSG.ShExJ.ShapeExternal")
        elif type(expression.valueExpr) == NoneType:
            logging.error("TODO None")
            node_dict[identifier][predicate] = "(1)"
        else:
            logging.error("Type not captured: " + str(type(expression.valueExpr)))
    else:
        logging.error("Fix me...")

def one_of_constraint(expression, identifier):
    logging.debug("one of constraints")
    for element in expression.expressions:
        if element.type == 'EachOf':
            each_of_constraint(element, identifier)
        else:
            logging.error("Not caputered")


def expressions(expressions, identifier):
    for expression in expressions:
        if expression["type"] == "TripleConstraint":
            triple_constraint(expression, identifier)
        else:
            logging.error("Not captured")


def set_prefix_map(shex_code):
    # print("shex_code", shex_code)
    for line in shex_code.splitlines():
        # print(">>>", line)
        if line.lower().startswith("base"):
            # print(line)
            line = line.replace("BASE", "").replace("base", "")
            uri = line.strip()
            prefix_map[uri.replace("<", "").replace(">", "")] = "base"
        elif line.lower().startswith("prefix"):
            # print(line)
            line = line.replace("PREFIX", "").replace("prefix", "")
            prefix, uri = line.split(": ")
            prefix = prefix.strip()
            uri = uri.strip()
            prefix_map[uri.replace("<", "").replace(">", "")] = prefix
    # print(prefix_map)


def each_of_constraint(each_of, identifier):
    for expression in each_of.expressions:
        if 'type' not in expression:
            if type(expression) == IRIREF:
                logging.debug("Not sure what to do with IRIREF here")
            else:
                logging.debug("NO TYPE")
        elif expression.type == "TripleConstraint":
            triple_constraint(expression, identifier)
        else:
            logging.debug("Nothing here yet")


def main(shex=shex_code, path="./uml_diagram"):
    # Reset objects
    global node_dict
    global edge_dict

    node_dict = {}
    edge_dict = {}

    # Set the prefixes from shex
    set_prefix_map(shex)
    # Create a schema loader
    loader = SchemaLoader()
    # Load schema as dictionary from json
    schema = loader.loads(shex)
    # print(schema)
    # x = schema._as_dict
    
    # Turn it into a dictionary
    # json_schema = json.loads(loader.loads(shex)._as_json)
    # print(schema)

    # Create a new Graphviz object
    dot = Digraph()
    dot.rankdir="TB"
    # Set the font for nodes and edges
    dot.attr('node', fontname='Courier New')
    dot.attr('edge', fontname='Courier New')
    # Set the default node and edge attributes
    dot.attr('node', shape='record')
    dot.attr('edge', arrowtail='empty', dir='back')

    # Iterate over each shape which will become a UML object
    if schema == None:
        return "Incompatible Shape Expression"
    
    for shape in schema.shapes:
        # check = json.loads(loader.loads(shex)._as_json)
        identifier = url_fix(shape.id)
        node_dict[identifier] = {}

        # For expressions
        if "expression" in shape and shape.expression is not None:
            if 'type' not in shape.expression:
                logging.debug("No type defined")
            elif shape.expression.type == "TripleConstraint":
                triple_constraint(shape["expression"], identifier)
            elif shape.expression.type == "EachOf":
                each_of_constraint(shape.expression, identifier)
            elif shape.expression.type == "OneOf":
                logging.debug("TODO process each of")
                one_of_constraint(shape["expression"], identifier)
            else:
                logging.debug("Some new expression type detected " + shape["expression"]["type"])
        elif type(shape.values) == JSGArray:
            values = get_values(shape.values)
            for predicate in values:
                node_dict[identifier][predicate] = " (1)"
        elif type(shape.shapeExprs) is JSGArray:
            print("TODO... working on shape.shapeExprs")
        else:
            logging.error("No expression found for " + shape.id)

    # Create the node
    for node in node_dict:
        content = "{" + escape_dot_string(node) + '|'
        for predicate in node_dict[node]:
            content += "+" + escape_dot_string(predicate) + " : " + escape_dot_string(
                node_dict[node][predicate]) + "\\l"
        content += '}'
        # Convert to raw string to get rid of crazy escapes
        content = r"%s" % content
        content = content.replace("\n", "\\n")
        dot.node(escape_dot_string(node), content)
        # print(">", node, content)

    for edge in edge_dict:
        for label in edge_dict[edge]:
            left, right = edge.split("#$#")
            # print("EDGE:", left, right)
            dot.edge(escape_dot_string(left), escape_dot_string(right), label)

    # Render the diagram to a file
    dot.attr(concentrate="true")

    if __name__ == '__main__':
        dot.render(path, format='svg')
    else:
        # Content xml cleanup only obtain the <svg></svg> part
        dot.save("test" + ".dot")
        content = '\n'.join(dot.pipe(format='svg').decode('utf-8').split("\n")[6:])
        content = content.replace("<svg width","<svg id=test-svg width")
        # Encode the SVG string using Base64
        # encoded_svg = base64.b64encode(content.encode('utf-8')).decode('ascii')
        # Pass the encoded SVG string to the HTML template
        return content


if __name__ == '__main__':
    # Define the ShEx code as a string
    shutil.rmtree("../storage/generated/")
    os.makedirs("../storage/generated/")
    for filename in sorted(os.listdir("../static/shapes/test/")):
        if filename != "biolink-model.shex": continue
        logging.info("Processing " + filename)
        shex_code = open("../static/shapes/test/" + filename).read()
        shutil.copy("../static/shapes/test/" + filename, "../storage/generated/" + filename)
        main(shex=shex_code, path="../storage/generated/" + filename.replace(".shex", ""))
