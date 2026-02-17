from app import create_app
from app.extensions import base



if __name__ == '__main__':
    app = create_app()
    base.create_pool()
    app.run(debug=True, host='0.0.0.0', port=8000)
