from src.config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SECRET_KEY = "test-secret-key"
    WTF_CSRF_ENABLED = False

    # Email settings (set to non-functional values for testing)
    MAIL_SERVER = "localhost"
    MAIL_PORT = 25
    MAIL_USE_TLS = False
    MAIL_USERNAME = None
    MAIL_PASSWORD = None

    # Translation service
    MS_TRANSLATOR_KEY = "dummy-key"

    # Disable error emails during testing
    ADMINS = []

    # Set small page sizes to test pagination with fewer records
    POSTS_PER_PAGE = 3
    GENES_PER_PAGE = 5
    RUNS_PER_PAGE = 3
