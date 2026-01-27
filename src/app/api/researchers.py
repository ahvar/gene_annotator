from src.app.api import bp


@bp.route("/researcher/<int:id>", methods=["GET"])
def get_researcher(id):
    pass


@bp.route("/researchers", methods=["GET"])
def get_researchers():
    pass


@bp.route("/researchers/<int:id>/followers", methods=["GET"])
def get_followers(id):
    pass


@bp.route("/researchers/<int:id>/following", methods=["GET"])
def get_following(id):
    pass


@bp.route("/researchers", methods=["POST"])
def create_researcher():
    pass


@bp.route("/researcher/<int:id>", methods=["PUT"])
def update_researcher(id):
    pass
