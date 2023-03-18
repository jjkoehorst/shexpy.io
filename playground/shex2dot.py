import graphviz
from ShExJSG.ShExJ import IRIREF, TripleConstraint, NodeConstraint, ObjectLiteral
from pyshex.utils.schema_loader import SchemaLoader

symbol = {
    "class": "oval",
    "datatype": "octagon",
    "literal": "rectangle",
    "iri": "diamond",
    "bnode": 'point',
    "oneof": 'record'
}


def shex2dot(shex, graphviz_name="default.png", rankdir="LR"):
    def process_tc(tc):
        dotschema.node(startshape.replace(":", ""), startshape, shape=symbol["iri"])
        if isinstance(tc, TripleConstraint):
            if tc.max == None and tc.min == None:
                arrowhead = "normal"
            elif tc.max == 1 and tc.min == 0:
                arrowhead = "teeodot"
            elif tc.max == -1 and tc.min == 1:
                arrowhead = "crowtee"
            elif tc.max == -1 and tc.min == 0:
                arrowhead = "crowdot"
            if isinstance(tc.valueExpr, IRIREF):
                node = tc.valueExpr
                predicate = tc.predicate
                for key in prefixmap.keys():
                    node = node.replace(key, prefixmap[key])
                    predicate = predicate.replace(key, prefixmap[key] + ":")
                dotschema.node(node, node, shape=symbol["iri"])
                dotschema.edge(shape.id.split("/")[-1], node, label=predicate, arrowhead=arrowhead)
            elif isinstance(tc.valueExpr, NodeConstraint):
                if tc.valueExpr.datatype:
                    datatype = tc.valueExpr.datatype
                    predicate = tc.predicate
                    for key in prefixmap.keys():
                        datatype = datatype.replace(key, prefixmap[key] + ":")
                        predicate = predicate.replace(key, prefixmap[key] + ":")
                    dotschema.node(
                        shape.id.split("/")[-1] + tc.valueExpr.datatype.split("/")[-1] + tc.predicate.split("/")[-1],
                        datatype, shape=symbol["datatype"])
                    dotschema.edge(shape.id.split("/")[-1],
                                   shape.id.split("/")[-1] + tc.valueExpr.datatype.split("/")[-1] +
                                   tc.predicate.split("/")[
                                       -1], label=predicate, arrowhead=arrowhead)
                elif tc.valueExpr.values:
                    oneofs = []
                    predicate = tc.predicate
                    for value in tc.valueExpr.values:
                        if isinstance(value, ObjectLiteral):
                            oneofs.append(value.value)
                        else:
                            for key in prefixmap.keys():
                                try:
                                    value = value.replace(key, prefixmap[key] + ":")
                                except:
                                    value = "a"
                            oneofs.append(value)
                    for key in prefixmap.keys():
                        predicate = predicate.replace(key, prefixmap[key] + ":")
                    dotschema.node(
                        shape.id.split("/")[-1] + "|".join(oneofs).replace(":", "") + tc.predicate.split("/")[-1],
                        "{" + "|".join(oneofs) + "}", shape=symbol["oneof"])
                    dotschema.edge(shape.id.split("/")[-1],
                                   shape.id.split("/")[-1] + "|".join(oneofs).replace(":", "") +
                                   tc.predicate.split("/")[
                                       -1], label=predicate)

                elif tc.valueExpr.nodeKind:
                    dotschema.node(tc.valueExpr.nodeKind, tc.valueExpr.nodeKind.split("/")[-1],
                                   shape=symbol[tc.valueExpr.nodeKind])
                    dotschema.edge(shape.id.split("/")[-1], tc.valueExpr.nodeKind.split("/")[-1],
                                   label=tc.predicate.split("/")[-1], arrowhead="teedot")
                elif tc.valueExpr.xone:

                    dotschema.node(tc.valueExpr.xone[0].identifier, tc.valueExpr.xone[0].identifier.split("/")[-1],
                                   shape=symbol["oneof"])
                    dotschema.edge(shape.id.split("/")[-1], tc.valueExpr.xone[0].identifier.split("/")[-1],
                                   label=tc.predicate.split("/")[-1], arrowhead="teedot")
                else:
                    pass
                    # print("No valueExpr")
            else:
                pass
                # print("No valueExpr")

    dotschema = graphviz.Digraph(graphviz_name, format="png")
    dotschema.attr(rankdir=rankdir)
    prefixmap = dict()
    for line in shex.splitlines():
        if line.startswith("PREFIX"):
            line = line.replace("PREFIX", "")
            prefix, uri = line.split(": ")
            prefix = prefix.strip()
            uri = uri.strip()
            prefixmap[uri.replace("<", "").replace(">", "")] = prefix
            dotschema.node(prefix, uri, shape="none", style="invis")

    loader = SchemaLoader()
    schema = loader.loads(shex)

    for shape in schema.shapes:
        if id in (dir(shape)):
            continue
        startshape = shape.id
        for key in prefixmap.keys():
            startshape = startshape.replace(key, prefixmap[key] + ":")
        if "expressions" in dir(shape.expression):
            for tc in shape.expression.expressions:
                process_tc(tc)
        else:
            tc = shape.expression
            process_tc(tc)

    return dotschema


def view_graphviz(dotschema):
    return dotschema.view()


def save_graphviz(dotschema, filename):
    return dotschema.render(filename)
