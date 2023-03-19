import base64
import json
import os
import shutil

import ShExJSG
import validators
from ShExJSG.ShExJ import TripleConstraint, IRIREF
from graphviz import Digraph
from pyshex.utils.schema_loader import SchemaLoader

# Placeholder for URL prefixes
prefix_map = dict()
shex_code: str = ""
# Create a new node and edge dict container
node_dict = {}
edge_dict = {}


def get_dict_size(d):
    size = 0
    if isinstance(d, dict):
        for k, v in d.items():
            size += get_dict_size(k) + get_dict_size(v)
    elif isinstance(d, list):
        size += len(d) * get_dict_size(d[0]) if d else 0
    elif isinstance(d, str):
        size += len(d.encode('utf-8'))
    else:
        size += d.__sizeof__()
    return size


# helper function to replace URL prefixes with their abbreviations
def url_fix(url):
    if validators.url(str(url)):
        url = str(url)
    if type(url) != str and not validators.url(str(url)):
        print("Not a url string: ", url)
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
        node_dict[identifier][predicate] = "" + "|".join(values) + ""
    elif "pattern" in shape["expression"]["valueExpr"]:
        node_dict[identifier][predicate] = shape["expression"]["valueExpr"]["pattern"]


def get_values(values_expression):
    values = set()
    for value in values_expression: # valueExpr["values"]:
        # Not sure if we need to fix the url
        if type(value) == dict and 'value' in value:
            value = url_fix(value['value'])
        elif type(value) == str:
            value = url_fix(value)
        elif type(value) == IRIREF:
            value = url_fix(str(value))
        else:
            print("Something else? ", type(value))
            value = ""
        values.add(value.strip())
    values = list(values)
    if len(values) > 5:
        new_values = []
        for index, value in enumerate(values):
            if index % 5 == 0:
                new_values.append("\\n")
            new_values.append(value)
        values = new_values
    return values

def triple_constraint(expression, identifier):
    global node_dict
    global edge_dict
    predicate = url_fix(expression.predicate)
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
                node_dict[identifier][predicate] = "[" + "\|".join(values).replace("\\|\\n",
                                                                                   "\\n") + "] (" + cardinality + ")"
            elif type(expression.valueExpr.datatype) == IRIREF:
                node_dict[identifier][predicate] = url_fix(str(expression.valueExpr.datatype)) + " (" + cardinality + ")"
        elif type(expression.valueExpr) == IRIREF:
            left = identifier
            right = url_fix(expression['valueExpr'])
            # print("left", left)
            # print("right", right)
            if left + "###" + right not in edge_dict:
                edge_dict[left + "#$#" + right] = []

            edge_dict[left + "#$#" + right].append(predicate)
        elif type(expression['valueExpr']) == ShExJSG.ShExJ.Shape:
            valueExpr = expression['valueExpr']
            if 'datatype' in valueExpr:
                node_dict[identifier][predicate] = url_fix(valueExpr['datatype']) + " (" + cardinality + ")"
            elif 'values' in valueExpr:
                values = get_values(valueExpr['values'])
                node_dict[identifier][predicate] = "[" + "\|".join(values).replace("\\|\\n",
                                                                                 "\\n") + "] (" + cardinality + ")"
            elif 'expression' in valueExpr:
                if type(valueExpr.expression) == TripleConstraint:
                    triple_constraint(valueExpr.expression, identifier)
            else:
                print("Need to capture something else...")
        else:
            print("Type not captured: ", type(expression['valueExpr']))
    else:
        print("Fix me...")
    # elif "min" in expression:
    #     node_dict[identifier][predicate] = str(expression["min"]) + ":" + str(expression["max"])
    # else:
    #     node_dict[identifier][predicate] = "<UNKNOWN>"


def one_of_constraint(expression, identifier):
    print("one of constraints")
    for element in expression.expressions:
        if element.type == 'EachOf':
            each_of_constraint(element, identifier)


def expressions(expressions, identifier):
    for expression in expressions:
        if expression["type"] == "TripleConstraint":
            triple_constraint(expression, identifier)


def set_prefix_map(shex_code):
    for line in shex_code.splitlines():
        if line.lower().startswith("base"):
            line = line.replace("BASE", "").replace("base", "")
            uri = line.strip()
            prefix_map[uri.replace("<", "").replace(">", "")] = "base"
        if line.lower().startswith("prefix"):
            line = line.replace("PREFIX", "").replace("prefix", "")
            prefix, uri = line.split(": ")
            prefix = prefix.strip()
            uri = uri.strip()
            prefix_map[uri.replace("<", "").replace(">", "")] = prefix


def each_of_constraint(each_of, identifier):
    for expression in each_of.expressions:
        if 'type' not in expression:
            print("NO TYPE")
        elif expression.type == "TripleConstraint":
            triple_constraint(expression, identifier)
        else:
            print("Nothing here yet")


def main(shex=shex_code, path="./uml_diagram"):
    # Reset objects
    global node_dict
    global edge_dict

    node_dict = {}
    edge_dict = {}

    # Set the prefixes from shex
    set_prefix_map(shex_code)
    # Create a schema loader
    loader = SchemaLoader()
    # Load schema as dictionary from json
    schema = loader.loads(shex)

    json_schema = json.loads(loader.loads(shex)._as_json)
    # Process shape
    # print(schema)

    # Create a new Graphviz object
    dot = Digraph()
    # Set the font for nodes and edges
    dot.attr('node', fontname='Courier New')
    dot.attr('edge', fontname='Courier New')
    # Set the default node and edge attributes
    dot.attr('node', shape='record')
    dot.attr('edge', arrowtail='empty', dir='back')

    # Iterate over each shape which will become a UML object
    for shape in schema.shapes:
        # check = json.loads(loader.loads(shex)._as_json)
        identifier = url_fix(shape.id)
        node_dict[identifier] = {}

        # For expressions
        # print(shape.expression)
        if "expression" in shape and shape.expression != None:
            if 'type' not in shape.expression:
                print("No type defined")
            elif shape.expression.type == "TripleConstraint":
                print(get_dict_size(node_dict), get_dict_size(edge_dict))
                triple_constraint(shape["expression"], identifier)
                # print(get_dict_size(node_dict), get_dict_size(edge_dict))
            elif shape.expression.type == "EachOf":
                each_of_constraint(shape.expression, identifier)
            elif shape.expression.type == "OneOf":
                print("TODO process each of")
                one_of_constraint(shape["expression"], identifier)
            # elif "valueExpr" in shape["expression"]:
            #     print("HERE!!!")
            #     # NodeConstraint
            #     if shape["expression"]["valueExpr"]["type"] == "NodeConstraint":
            #         node_constraint(shape, identifier)
            #     # Shape object
            #     elif shape["expression"]["valueExpr"]["type"] == "Shape":
            #         pass
            #     else:
            #         print("Something new!")
            else:
                print("Some new expression type detected", shape["expression"]["type"])
            # For general expressions
            # elif "expressions" in shape["expression"]:
            #     for expression in shape["expression"]["expressions"]:
            #         if type(expression) != dict:
            #             print("Expression not a dict")
            #         elif expression["type"] == "OneOf":
            #             pass
            #         else:
            #             print("Some new expression type detected", expression)

    # Create the node
    for node in node_dict:
        content = "{" + escape_dot_string(node) + '|'
        for predicate in node_dict[node]:
            content += "+" + escape_dot_string(predicate) + " : " + escape_dot_string(
                node_dict[node][predicate]) + "\\l"
        content += '}'
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
        content = '\n'.join(dot.pipe(format='svg').decode('utf-8').split("\n")[6:])
        # Encode the SVG string using Base64
        encoded_svg = base64.b64encode(content.encode('utf-8')).decode('ascii')
        # Pass the encoded SVG string to the HTML template
        return encoded_svg


if __name__ == '__main__':
    # Define the ShEx code as a string
    shutil.rmtree("../storage/generated/")
    os.makedirs("../storage/generated/")
    for filename in sorted(os.listdir("../static/shapes/test/")):
        # if filename != "E4.shex": continue
        print("Processing", filename)
        shex_code = open("../static/shapes/test/" + filename).read()
        shutil.copy("../static/shapes/test/" + filename, "../storage/generated/" + filename)
        main(shex=shex_code, path="../storage/generated/" + filename.replace(".shex", ""))
