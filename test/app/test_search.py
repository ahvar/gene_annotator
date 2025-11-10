import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from test.app.test_config import TestConfig
from src.app.models.researcher import Researcher, Post
from src.app import create_app, db


class MockElasticsearch:
    def index(self, *args, **kwargs):
        return True

    def search(self, *args, **kwargs):
        return {"hits": {"total": {"value": 0}, "hits": []}}

    def delete(self, *args, **kwargs):
        return True

    @classmethod
    def reindex(cls):
        pass


def mock_reindex():
    pass


add_to_index_patch = patch("src.app.search.add_to_index", lambda *args, **kwrgs: None)
remove_from_index_patch = patch(
    "src.app.search.remove_from_index", lambda *args, **kwargs: None
)


class TestSearchFunctionality(unittest.TestCase):
    def setUp(self):
        # Mock Elasticsearch for testing
        self.es_patcher = patch(
            "src.app.__init__.Elasticsearch", return_value=MockElasticsearch
        )
        self.mock_es = self.es_patcher.start()

        # Patch search functions to track calls
        self.add_to_index_patcher = patch("src.app.search.add_to_index")
        self.remove_from_index_patcher = patch("src.app.search.remove_from_index")
        self.query_index_patcher = patch("src.app.search.query_index")

        self.mock_add_to_index = self.add_to_index_patcher.start()
        self.mock_remove_from_index = self.remove_from_index_patcher.start()
        self.mock_query_index = self.query_index_patcher.start()

        # Configure mock query_index to return predictable results
        self.mock_query_index.return_value = ([1, 2], 2)

        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create test researchers
        self.researcher1 = Researcher(researcher_name="john", email="john@example.com")
        self.researcher2 = Researcher(researcher_name="jane", email="jane@example.com")
        db.session.add_all([self.researcher1, self.researcher2])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

        self.es_patcher.stop()
        self.add_to_index_patcher.stop()
        self.remove_from_index_patcher.stop()
        self.query_index_patcher.stop()

    def test_add_to_index_on_post_creation(self):
        """Test that creating a post automatically adds it to the search index"""
        # Reset mock call counts
        self.mock_add_to_index.reset_mock()

        # Create a post
        post = Post(
            body="This is a test post about Flask",
            author=self.researcher1,
            timestamp=datetime.now(timezone.utc),
        )
        db.session.add(post)
        db.session.commit()

        # Verify add_to_index was called
        self.mock_add_to_index.assert_called_once()
        call_args = self.mock_add_to_index.call_args[0]
        self.assertEqual(call_args[0], "post")  # index name
        self.assertEqual(call_args[1].body, "This is a test post about Flask")

    def test_update_index_on_post_modification(self):
        """Test that modifying a post updates the search index"""
        # Create and commit a post first
        post = Post(
            body="Original post content",
            author=self.researcher1,
            timestamp=datetime.now(timezone.utc),
        )
        db.session.add(post)
        db.session.commit()

        # Reset mock to track updates
        self.mock_add_to_index.reset_mock()

        # Modify the post
        post.body = "Updated post content"
        db.session.commit()

        # Verify add_to_index was called for the update
        self.mock_add_to_index.assert_called_once()
        call_args = self.mock_add_to_index.call_args[0]
        self.assertEqual(call_args[1].body, "Updated post content")

    def test_remove_from_index_on_post_deletion(self):
        """Test that deleting a post removes it from the search index"""
        # Create a post
        post = Post(
            body="Post to be deleted",
            author=self.researcher1,
            timestamp=datetime.now(timezone.utc),
        )
        db.session.add(post)
        db.session.commit()

        # Reset mock to track deletions
        self.mock_remove_from_index.reset_mock()

        # Delete the post
        post_id = post.id
        db.session.delete(post)
        db.session.commit()

        # Verify remove_from_index was called
        self.mock_remove_from_index.assert_called_once()
        call_args = self.mock_remove_from_index.call_args[0]
        self.assertEqual(call_args[0], "post")  # index name

    def test_search_functionality(self):
        """Test the search functionality returns correct results"""
        # Create test posts
        post1 = Post(
            body="Python Flask tutorial",
            author=self.researcher1,
            timestamp=datetime.now(timezone.utc),
        )
        post2 = Post(
            body="JavaScript React framework",
            author=self.researcher2,
            timestamp=datetime.now(timezone.utc),
        )
        db.session.add_all([post1, post2])
        db.session.commit()

        # Configure mock to return specific post IDs
        self.mock_query_index.return_value = ([post1.id], 1)

        # Perform search
        results, total = Post.search("Flask", 1, 10)

        # Verify query_index was called with correct parameters
        self.mock_query_index.assert_called_with("post", "Flask", 1, 10)

        # Verify results (Note: In real implementation, this would return actual Post objects)
        self.assertEqual(total, 1)

    def test_search_with_no_results(self):
        """Test search behavior when no results are found"""
        # Configure mock to return no results
        self.mock_query_index.return_value = ([], 0)

        # Perform search
        results, total = Post.search("nonexistent", 1, 10)

        # Verify no results returned
        self.assertEqual(total, 0)
        self.assertEqual(list(results), [])

    def test_search_pagination(self):
        """Test search functionality with pagination"""
        # Create multiple test posts
        posts = []
        for i in range(5):
            post = Post(
                body=f"Test post number {i}",
                author=self.researcher1,
                timestamp=datetime.now(timezone.utc),
            )
            posts.append(post)

        db.session.add_all(posts)
        db.session.commit()

        # Configure mock for paginated results
        self.mock_query_index.return_value = ([posts[0].id, posts[1].id], 5)

        # Test first page
        results, total = Post.search("Test", 1, 2)

        # Verify pagination parameters passed correctly
        self.mock_query_index.assert_called_with("post", "Test", 1, 2)
        self.assertEqual(total, 5)

    def test_reindex_functionality(self):
        """Test the reindex class method"""
        # Create test posts
        post1 = Post(
            body="First post for reindexing",
            author=self.researcher1,
            timestamp=datetime.now(timezone.utc),
        )
        post2 = Post(
            body="Second post for reindexing",
            author=self.researcher2,
            timestamp=datetime.now(timezone.utc),
        )
        db.session.add_all([post1, post2])
        db.session.commit()

        # Reset mock to track reindex calls
        self.mock_add_to_index.reset_mock()

        # Call reindex
        Post.reindex()

        # Verify add_to_index was called for each post
        self.assertEqual(self.mock_add_to_index.call_count, 2)

        # Verify correct posts were indexed
        call_args_list = self.mock_add_to_index.call_args_list
        indexed_bodies = [call[0][1].body for call in call_args_list]
        self.assertIn("First post for reindexing", indexed_bodies)
        self.assertIn("Second post for reindexing", indexed_bodies)

    def test_manual_add_to_index(self):
        """Test manually adding a post to the index"""
        post = Post(
            body="Manual indexing test",
            author=self.researcher1,
            timestamp=datetime.now(timezone.utc),
        )
        db.session.add(post)
        db.session.commit()

        # Reset mock
        self.mock_add_to_index.reset_mock()

        # Manually add to index
        post.add_to_index()

        # Verify add_to_index was called
        self.mock_add_to_index.assert_called_once()
        call_args = self.mock_add_to_index.call_args[0]
        self.assertEqual(call_args[0], "post")
        self.assertEqual(call_args[1], post)

    def test_manual_remove_from_index(self):
        """Test manually removing a post from the index"""
        post = Post(
            body="Manual removal test",
            author=self.researcher1,
            timestamp=datetime.now(timezone.utc),
        )
        db.session.add(post)
        db.session.commit()

        # Manually remove from index
        post.remove_from_index()

        # Verify remove_from_index was called
        self.mock_remove_from_index.assert_called_once()
        call_args = self.mock_remove_from_index.call_args[0]
        self.assertEqual(call_args[0], "post")
        self.assertEqual(call_args[1], post)

    def test_searchable_attribute_exists(self):
        """Test that Post model has the __searchable__ attribute"""
        self.assertTrue(hasattr(Post, "__searchable__"))
        self.assertIn("body", Post.__searchable__)
