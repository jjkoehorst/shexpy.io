import base64
import json

from graphviz import Digraph
from pyshex.utils.schema_loader import SchemaLoader

# Define the ShEx code as a string
shex_code = '''
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>

start = @<human>

<human> EXTRA wdt:P31 {
  wdt:P31 [wd:Q5];
  wdt:P18 . * ;               # image (portrait)
  wdt:P21 [wd:Q48270 wd:Q48279 wd:Q179294 wd:Q189125 wd:Q207959 wd:Q301702 wd:Q350374 wd:Q505371 wd:Q660882 wd:Q746411 wd:Q859614 wd:Q1052281 wd:Q1097630 wd:Q1289754 wd:Q1399232 wd:Q2449503 wd:Q3177577 wd:Q3277905 wd:Q6581072 wd:Q6581097 wd:Q7130936 wd:Q12964198 wd:Q15145778 wd:Q15145779 wd:Q18116794 wd:Q27679684 wd:Q27679766 wd:Q52261234 wd:Q93954933 wd:Q93955709 wd:Q96000630 wd:Q25388691 wd:Q56315990]?;   # gender
  wdt:P19 . ?;                      # place of birth
  wdt:P20 . ?;                      # place of death
  wdt:P569 . ? ;                    # date of birth
  wdt:P570 . ? ;                   # date of death
  wdt:P735 . * ;                    # given name
  wdt:P734 . * ;                    # family name
  wdt:P106 . * ;                    # occupation
  wdt:P1559 . ? ;              #name in native language
  wdt:P27 @<country> *;           # country of citizenship
  wdt:P22 @<human> *;             # father
  wdt:P25 @<human> *;             # mother
  wdt:P3373 @<human> *;           # sibling
  wdt:P26 @<human> *;             # spouse
  wdt:P40 @<human> *;             # children
  wdt:P1038 @<human> *;           # relatives
  wdt:P103 @<language> *;         # native language
  wdt:P1412 @<language> *;        # languages spoken, written or signed
  wdt:P6886  @<language> *;       # writing language
  rdfs:label rdf:langString+;
}

<country> EXTRA wdt:P31 {
  wdt:P31 [wd:Q6256 wd:Q3024240 wd:Q3624078] +;
}

<language> EXTRA wdt:P31 {
  wdt:P31 [wd:Q34770 wd:Q1288568] +;
}
'''

shex_code = '''
PREFIX : <http://hl7.org/fhir/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX entity: <http://www.wikidata.org/entity/>

start = @<ObservationShape>

<ObservationShape> {               # An Observation has:
  :status ["preliminary" "final"]; #   status in this value set
  :subject @<PatientShape>         #   a subject matching <PatientShape>.
}

<PatientShape> {                   # A Patient has:
 :name xsd:string*;                #   one or more names
 :birthdate xsd:date?              #   and an optional birthdate.
}
'''

# Placeholder for URL prefixes
prefixmap = dict()


# helper function to replace URL prefixes with their abbreviations
def url_fix(url):
    for key in prefixmap:
        if url.startswith(key):
            # replace the URL with its corresponding prefix
            return url.replace(key, prefixmap[key] + ";")
    return url

# main function to generate the UML diagram
def main(shex=shex_code, path="./uml_diagram"):
    for line in shex.splitlines():
        if line.startswith("PREFIX") or line.startswith("prefix"):
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
    print(schema)

    # Create a new Graphviz object
    dot = Digraph()
    # Set the font for nodes and edges
    dot.attr('node', fontname='Courier New')
    dot.attr('edge', fontname='Courier New')
    # Set the default node and edge attributes
    dot.attr('node', shape='record')
    dot.attr('edge', arrowtail='empty', dir='back')

    # Create a new node dict
    node_dict = {}
    edge_dict = {}
    # Iterate over each shape
    for shape in schema["shapes"]:
        identifier = shape["id"]
        node_dict[identifier] = {}

        # For valueExpressions
        if "valueExpr" in shape["expression"]:
            if shape["expression"]["valueExpr"]["type"] == "NodeConstraint":
                predicate = url_fix(shape["expression"]["predicate"])
                values = set()
                for value in shape["expression"]["valueExpr"]["values"]:
                    value = url_fix(value)
                values.add(value)
                node_dict[identifier][predicate] = "" + "|".join(values) + ""
            else:
                print("Something new!")
        # For general expressions
        if "expressions" in shape["expression"]:
            for expression in shape["expression"]["expressions"]:
                if expression["type"] != "TripleConstraint":
                    print("Not a triple constraint?")
                else:
                    predicate = url_fix(expression["predicate"])
                    if "valueExpr" in expression:
                        # print(identifier, predicate, expression['valueExpr'])
                        # Draw a connection!
                        if type(expression['valueExpr']) == str:
                            left = identifier
                            right = expression['valueExpr']
                            print("left", left)
                            print("right", right)
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
                                    value = url_fix(value['value'])
                                    values.add(value.strip())
                                node_dict[identifier][predicate] = "[" + "\|".join(values) + "]"

                    elif "min" in expression:
                        node_dict[identifier][predicate] = str(expression["min"]) + ":" + str(expression["max"])
                    else:
                        values = set()
                        for value in expression["valueExpr"]["values"]:
                            value = url_fix(value)
                        values.add(value)
                        node_dict[identifier][predicate] = "" + "|".join(values) + ""

    # Create the node
    for node in node_dict:
        content = "{" + node + '|'
        for predicate in node_dict[node]:
            content += "+" + predicate + " : " + node_dict[node][predicate] + "\\l"
        content += '}'
        dot.node(node, content)
        print(">", node, content)

    for edge in edge_dict:
        for label in edge_dict[edge]:
            left, right = edge.split("###")
            print(left, right, label)
            dot.edge(left, right, label)

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
    main()
