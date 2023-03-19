import base64
import json
import os

import validators
from graphviz import Digraph
from pyshex.utils.schema_loader import SchemaLoader

# Placeholder for URL prefixes
prefixmap = dict()
shex_code = ""
# Create a new node dict
node_dict = {}
edge_dict = {}


# helper function to replace URL prefixes with their abbreviations
def url_fix(url):
    if type(url) != str:
        print("Not a url string: ", url)
        return ""
    if not validators.url(url):
        return url
    for key in prefixmap:
        if url.startswith(key):
            # replace the URL with its corresponding prefix
            return url.replace(key, prefixmap[key] + ":")
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


def main(shex=shex_code, path="./uml_diagram"):
    # print("SHEX_CODE:", shex)
    for line in shex.splitlines():
        if line.lower().startswith("base"):
            line = line.replace("BASE", "").replace("base", "")
            uri = line.strip()
            prefixmap[uri.replace("<", "").replace(">", "")] = "base"
        if line.lower().startswith("prefix"):
            line = line.replace("PREFIX", "").replace("prefix", "")
            prefix, uri = line.split(": ")
            prefix = prefix.strip()
            uri = uri.strip()
            prefixmap[uri.replace("<", "").replace(">", "")] = prefix

    # Create a schema loader
    loader = SchemaLoader()
    # Load schema as dictionary from json
    schema = json.loads(loader.loads(shex)._as_json)
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

    # Iterate over each shape
    for shape in schema["shapes"]:
        identifier = url_fix(shape["id"])
        node_dict[identifier] = {}

        # For valueExpressions
        if "expression" in shape:
            if shape["expression"]["type"] == "TripleConstraint":
                pass
            if "valueExpr" in shape["expression"]:
                # NodeConstraint
                if shape["expression"]["valueExpr"]["type"] == "NodeConstraint":
                    node_constraint(shape, identifier)
                # Shape object
                elif shape["expression"]["valueExpr"]["type"] == "Shape":
                    pass
                else:
                    print("Something new!")
            # For general expressions
            if "expressions" in shape["expression"]:
                for expression in shape["expression"]["expressions"]:
                    if type(expression) != dict:
                        print("Expression not a dict")
                    elif expression["type"] == "OneOf":
                        pass
                    elif expression["type"] == "TripleConstraint":
                        predicate = url_fix(expression["predicate"])
                        if "valueExpr" in expression:
                            # print(identifier, predicate, expression['valueExpr'])
                            # Draw a connection!
                            if type(expression['valueExpr']) == str:
                                left = identifier
                                right = url_fix(expression['valueExpr'])
                                # print("left", left)
                                # print("right", right)
                                if left + "###" + right not in edge_dict:
                                    edge_dict[left + "###" + right] = []

                                edge_dict[left + "###" + right].append(predicate)
                            elif type(expression['valueExpr']) == dict:
                                if 'datatype' in expression['valueExpr']:
                                    node_dict[identifier][predicate] = url_fix(expression['valueExpr']['datatype'])
                                elif 'values' in expression['valueExpr']:
                                    values = set()
                                    for value in expression["valueExpr"]["values"]:
                                        # Not sure if we need to fix the url
                                        if type(value) == dict and 'value' in value:
                                            value = url_fix(value['value'])
                                        elif type(value) == str:
                                            value = url_fix(value)
                                        else:
                                            print("Something else?")
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
                                    node_dict[identifier][predicate] = "[" + "\|".join(values).replace("\\|\\n",
                                                                                                       "\\n") + "]"

                        elif "min" in expression:
                            node_dict[identifier][predicate] = str(expression["min"]) + ":" + str(expression["max"])
                        else:
                            values = set()
                            for value in expression["valueExpr"]["values"]:
                                value = url_fix(value)
                            values.add(value)
                            node_dict[identifier][predicate] = "" + "|".join(values) + ""
                    else:
                        print("Some new expression type detected", expression)

    # Create the node
    for node in node_dict:
        content = "{" + escape_dot_string(node) + '|'
        for predicate in node_dict[node]:
            content += "+" + escape_dot_string(predicate) + " : " + escape_dot_string(node_dict[node][predicate]) + "\\l"
        content += '}'
        dot.node(escape_dot_string(node), content)
        # print(">", node, content)

    for edge in edge_dict:
        for label in edge_dict[edge]:
            left, right = edge.split("###")
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
    for filename in os.listdir("../static/shapes/test/"):
        print("Processing", filename)
        shex_code = open("../static/shapes/test/" + filename).read()
        main(shex=shex_code, path="../storage/generated/" + filename)
