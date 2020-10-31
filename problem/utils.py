import re

TEMPLATE_BASE = """{}

//write code start here

//write code end here 

{}
"""


def parse_problem_template(template_str):
    prepend = re.findall("//PREPEND BEGIN\n([\s\S]+?)//PREPEND END", template_str)
    template = re.findall("//TEMPLATE BEGIN\n([\s\S]+?)//TEMPLATE END", template_str)
    append = re.findall("//APPEND BEGIN\n([\s\S]+?)//APPEND END", template_str)
    return {"prepend": prepend[0] if prepend else "",
            "template": template[0] if template else "",
            "append": append[0] if append else ""}


def build_problem_template(prepend, append):
    return TEMPLATE_BASE.format(prepend, append)
