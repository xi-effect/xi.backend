from re import fullmatch, sub
from typing import List, Tuple, Set, Dict, Callable

server_folder: str = "D:/Important/Xi Effect [EFES]/"
try:
    open(server_folder + "main.py", "rb")
except FileNotFoundError:
    server_folder = "D:/Projects/Xi Effect [EFES]/"

file_queue: Dict[str, List[str]] = {
    "": ["main", "api", "updater"],
    "database": {
        "base": ["addons", "basic"],
        "education": ["courses", "moderation", "session"],
        "users": ["authors", "users", "special"],
        "file_system": ["keeper"],
        "outside": ["tester"]
    },
    "api_resources": {
        "base": ["parsers", "checkers", "discorder", "emailer"],
        "education": ["authorship", "courses", "education",
                      "publishing", "wip_files"],
        "outside": ["applications", "basic", "olympiada"],
        "users": ["confirmer", "reglog", "settings"]
    }
}

result_filepath: str = "unifile_server.py"
imports: Dict[str, Set[str]] = dict()
production: bool = False


def read_file(filename: str) -> Tuple[str, str]:
    global imports, production
    result: str = ""
    footer: str = ""
    temp1: List[str]
    line: str

    with open(filename + ".py", "r") as f:
        temp1 = f.read().split("\n")

    for line in temp1:
        if fullmatch(r"from .+ import .+", line):
            if not fullmatch(r"from (api_resources|database|emails|main|api|bot)\.?.* import .*", line):
                temp: List[str] = line[5:].split(" import ", 1)
                importing: Set[str] = set(temp[1].split(", "))
                if temp[0] in imports.keys():
                    imports[temp[0]].update(importing)
                else:
                    imports[temp[0]] = importing
        elif fullmatch(r"api\.add_resource\(.*\)", line):
            footer += line + "\n"
        elif fullmatch(r"app.config\[\"SQLALCHEMY_DATABASE_URI\"] = .*", line):
            result += "app.config[\"SQLALCHEMY_DATABASE_URI\"] = \"sqlite:///app.db\"\n"
        elif not (fullmatch(r" *#.*|.*app.run\(.*\)|if __name__ == \"__main__\":.*", line) or
                  (production and fullmatch(r".*# no_prod", line))):
            result += line + "\n"

    return result, footer


def recursive_file_reading(path: str, file_queue: dict, operation: Callable[[str, str], None]):
    for subfolder in file_queue.keys():
        content = file_queue[subfolder]
        if isinstance(content, dict):
            recursive_file_reading(path + "/" + subfolder, content, operation)
        else:
            for filename in file_queue[subfolder]:
                operation(path + "/" + subfolder, filename)


if __name__ == "__main__":


    result: str = ""
    footer: str = ""

    def operation1(path: str, filename: str):
        global result, footer
        temp: tuple = read_file(path + "/" + filename)
        result += temp[0]
        footer += temp[1]

    recursive_file_reading(server_folder, file_queue, operation1)

    result_imports: List[str] = list()
    for module_name in imports.keys():
        temp1: str = f"from {module_name} import {', '.join(imports[module_name])}"
        temp2: str = ""
        while len(temp1) > 95:
            i: int = temp1[:95].rfind(",") + 1
            temp2 += temp1[:i] + "\\\n   "
            temp1 = temp1[i:]
        result_imports.append(temp2 + temp1)

    footer += """
if __name__ == "__main__":
    app.run(debug=True)
"""

    result_imports.sort(key=lambda x: len(x))
    result = sub(r"\n{4,}", "\n\n\n", "\n".join(result_imports) + "\n" + result[:-1] + "\n\n" + footer)

    with open(result_filepath, "w") as f:
        f.write(result)
