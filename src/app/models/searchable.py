import sqlalchemy as sa
from src.app import db, search


class SearchableMixin(object):
    """Mixin class that adds Elasticsearch functionality to a SQLAlchemy model.

    This mixin provides search capabilities to SQLAlchemy models by integrating
    with Elasticsearch. Models that use this mixin should define a
    `__searchable__` class attribute containing a list of the model fields
    that should be indexed in Elasticsearch.

    To use this mixin, add it as a parent class to your SQLAlchemy model:

    ```
    class MyModel(db.Model, SearchableMixin):
        __searchable__ = ['name', 'description']
        # model definition...
    ```

    The mixin relies on the app's Elasticsearch connection being configured
    correctly in the Flask application instance.
    """

    @classmethod
    def search(cls, expression, page, per_page):
        """Search for records matching the given expression.

        Performs a search using Elasticsearch and then retrieves the corresponding
        database records. Results are returned in the same order as ranked by
        Elasticsearch.

        Args:
            expression (str): The search query to execute
            page (int): The page number (1-based) for pagination
            per_page (int): Number of results per page

        Returns:
            tuple: A tuple containing:
                - A query result containing model instances matching the search
                - The total number of matching records

        Example:
            results, total = Post.search('flask tutorial', 1, 10)
        """
        ids, total = search.query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return [], 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        query = (
            sa.select(cls).where(cls.id.in_(ids)).order_by(db.case(*when, value=cls.id))
        )
        return db.session.scalars(query), total

    @classmethod
    def before_commit(cls, session):
        """Store changes before a commit occurs.

        This method is registered as a SQLAlchemy 'before_commit' event listener
        and captures all pending changes (additions, updates, deletions) in the
        session before they are committed to the database.

        Args:
            session: The SQLAlchemy session that is about to be committed

        Note:
            This method works with after_commit() to ensure that Elasticsearch
            indexes stay in sync with the database.
        """
        session._changes = {
            "add": list(session.new),
            "update": list(session.dirty),
            "delete": list(session.deleted),
        }

    @classmethod
    def after_commit(cls, session):
        """Process changes after a commit has occurred.

        This method is registered as a SQLAlchemy 'after_commit' event listener
        and updates the Elasticsearch index based on the database changes that
        were just committed. It adds new records, updates modified ones, and
        removes deleted ones from the search index.

        Args:
            session: The SQLAlchemy session that was just committed

        Note:
            This method relies on the changes captured by before_commit()
            to determine which records need to be updated in Elasticsearch.
        """
        for obj in session._changes["add"]:
            if isinstance(obj, SearchableMixin):
                search.add_to_index(obj.__tablename__, obj)

        for obj in session._changes["update"]:
            if isinstance(obj, SearchableMixin):
                search.add_to_index(obj.__tablename__, obj)
        for obj in session._changes["delete"]:
            if isinstance(obj, SearchableMixin):
                search.remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        """Rebuild the search index for this model class.

        This method retrieves all instances of the model from the database
        and adds them to the Elasticsearch index. This is useful when:
        - Setting up the search index for the first time
        - Rebuilding after an index becomes corrupted
        - Updating after changes to the indexed fields

        Example:
            # Rebuild the search index for the Post model
            Post.reindex()
        """
        for obj in db.session.scalars(sa.select(cls)):
            search.add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, "before_commit", SearchableMixin.before_commit)
db.event.listen(db.session, "after_commit", SearchableMixin.after_commit)
