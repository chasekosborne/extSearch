import os
from dotenv import load_dotenv
from flask import Flask, session

load_dotenv()


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-production")

    from index_server import index_bp
    from clients.fit import fit_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(fit_bp)

    from authTokens.flaskInterface import auth_bp,init_session

    init_session(app)
    app.register_blueprint(auth_bp)

    @app.context_processor
    def inject_user():
        return {
            "current_user_id": session.get("user_id"),
            "current_username": session.get("username"),
            "is_guest": session.get("is_guest", False),
        }

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True,threaded=False)
