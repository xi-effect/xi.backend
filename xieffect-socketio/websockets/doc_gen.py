def generate(title: str = "API", version: str = "1.0.0"):
    result = {
        "asyncapi": "2.2.0",
        "info": {
            "title": title,
            "version": version,
        },
        "channels": {
            "<some-channel>": {
                "description": "",
                "subscribe": {
                    # ServerEvent
                },
                "publish": {
                    # ClientEvent
                },
            },
        },
        "components": {
            "messages": {
                "name": "",
                "title": "",
                "summary": "",
                "description": "",
                "payload": {
                    # json schema
                },
            },
        },
    }

    event = {
        "summary": "",
        "description": "",
        "tags": [
            {
                "name": ""
            },
        ],
        "message": {
            "$ref": "#/components/messages/<some-message>"
        },
    }
