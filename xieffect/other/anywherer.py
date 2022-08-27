from os import environ

from requests import get, post, Response

headers: dict = {"Authorization": f"Token {environ['API_TOKEN']}"}
base_url: str = "https://www.pythonanywhere.com/api/v0/user/qwert45hi"

main_domain: str = "xieffect.ru"
dev_domain: str = "qwert45hi.pythonanywhere.com"


def execute_in_console(line: str, console_id: int = None) -> bool:
    if console_id is None:
        console_id = get(base_url + "/consoles/", headers=headers).json()[0]["id"]
    response: Response = post(
        base_url + f"/consoles/{console_id}/send_input/",
        json={"input": f"{line}\n"},
        headers=headers,
    )
    return response.status_code == 200


def execute_script_in_console(script_name: str, console_id: int = None) -> bool:
    return execute_in_console("python " + script_name, console_id)


def webapp_action(action: str, domain_name: str = dev_domain) -> bool:
    response: Response = post(
        base_url + f"/webapps/{domain_name}/{action}/", headers=headers
    )
    return 200 <= response.status_code <= 299


def enable_webapp(domain_name: str = dev_domain) -> bool:
    return webapp_action("enable", domain_name)


def disable_webapp(domain_name: str = dev_domain) -> bool:
    return webapp_action("disable", domain_name)


def reload_webapp(domain_name: str = dev_domain) -> bool:
    return webapp_action("reload", domain_name)
