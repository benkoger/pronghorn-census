from flask import jsonify


def handle_generic_http(error):
    return (
        jsonify(
            {"error": error.name, "code": error.code, "message": error.description}
        ),
        error.code,
    )


def internal_service_error(error):
    return (
        jsonify(
            {
                "error": "Internal Server Error",
                "code": 500,
                "message": "An unexpected error occurred on the server.",
            }
        ),
        500,
    )
