import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from test.app.test_config import TestConfig
from src.app.models.researcher import Researcher, Post, Notification, Message
from src.app import create_app, db
from test.app.test_search import (
    MockElasticsearch,
    mock_reindex,
    add_to_index_patch,
    remove_from_index_patch,
)


class TestResearcherModel(unittest.TestCase):
    def setUp(self):
        add_to_index_patch.start()
        remove_from_index_patch.start()
        self.es_patcher = patch(
            "src.app.__init__.Elasticsearch", return_value=MockElasticsearch
        )
        self.mock_es = self.es_patcher.start()
        self.reindex_patcher = patch(
            "src.app.models.searchable.SearchableMixin.reindex", mock_reindex
        )
        self.mock_reindex = self.reindex_patcher.start()
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

        self.es_patcher.stop()
        self.reindex_patcher.stop()

    def test_password_hashing(self):
        r = Researcher(researcher_name="susan", email="susan@example.com")
        r.set_password("cat")
        self.assertFalse(r.check_password("dog"))
        self.assertTrue(r.check_password("cat"))

    def test_avatar(self):
        r = Researcher(researcher_name="john", email="john@example.com")
        self.assertEqual(
            r.avatar(128),
            (
                "https://www.gravatar.com/avatar/"
                "d4c74594d841139328695756648b6bd6"
                "?d=identicon&s=128"
            ),
        )

    def test_follow(self):
        r1 = Researcher(researcher_name="john", email="john@example.com")
        r2 = Researcher(researcher_name="susan", email="susan@example.com")
        db.session.add(r1)
        db.session.add(r2)
        db.session.commit()
        following = db.session.scalars(r1.following.select()).all()
        followers = db.session.scalars(r2.followers.select()).all()
        self.assertEqual(following, [])
        self.assertEqual(followers, [])

        r1.follow(r2)
        db.session.commit()
        self.assertTrue(r1.is_following(r2))
        self.assertEqual(r1.following_count(), 1)
        self.assertEqual(r2.followers_count(), 1)
        u1_following = db.session.scalars(r1.following.select()).all()
        u2_followers = db.session.scalars(r2.followers.select()).all()
        self.assertEqual(u1_following[0].researcher_name, "susan")
        self.assertEqual(u2_followers[0].researcher_name, "john")

        r1.unfollow(r2)
        db.session.commit()
        self.assertFalse(r1.is_following(r2))
        self.assertEqual(r1.following_count(), 0)
        self.assertEqual(r2.followers_count(), 0)

    def test_follow_posts(self):
        # create four users
        r1 = Researcher(researcher_name="john", email="john@example.com")
        r2 = Researcher(researcher_name="susan", email="susan@example.com")
        r3 = Researcher(researcher_name="mary", email="mary@example.com")
        r4 = Researcher(researcher_name="david", email="david@example.com")
        db.session.add_all([r1, r2, r3, r4])

        # create four posts
        now = datetime.now(timezone.utc)
        p1 = Post(
            body="post from john", author=r1, timestamp=now + timedelta(seconds=1)
        )
        p2 = Post(
            body="post from susan", author=r2, timestamp=now + timedelta(seconds=4)
        )
        p3 = Post(
            body="post from mary", author=r3, timestamp=now + timedelta(seconds=3)
        )
        p4 = Post(
            body="post from david", author=r4, timestamp=now + timedelta(seconds=2)
        )
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        # setup the followers
        r1.follow(r2)  # john follows susan
        r1.follow(r4)  # john follows david
        r2.follow(r3)  # susan follows mary
        r3.follow(r4)  # mary follows david
        db.session.commit()

        # check the following posts of each user
        f1 = db.session.scalars(r1.following_posts()).all()
        f2 = db.session.scalars(r2.following_posts()).all()
        f3 = db.session.scalars(r3.following_posts()).all()
        f4 = db.session.scalars(r4.following_posts()).all()
        self.assertEqual(f1, [p2, p4, p1])
        self.assertEqual(f2, [p2, p3])
        self.assertEqual(f3, [p3, p4])
        self.assertEqual(f4, [p4])

    def test_add_notification(self):
        r1 = Researcher(researcher_name="john", email="john@example.com")
        db.session.add(r1)
        db.session.commit()
        # add a notification using the model method
        test_data = {"message": "test notification data"}
        notification = r1.add_notification("test1", test_data)
        db.session.commit()
        # verify notification was created
        self.assertIsNotNone(notification)
        self.assertEqual(notification.name, "test1")
        self.assertEqual(notification.researcher_id, r1.id)
        self.assertEqual(notification.get_data(), test_data)
        # test that adding another notification with same name replaces the first
        updated_data = {"message": "updated notification data"}
        notification2 = r1.add_notification("test1", updated_data)
        db.session.commit()
        # verify only one notification exists with the updated data
        notifications = db.session.scalars(
            r1.notifications.select().where(Notification.name == "test1")
        ).all()
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].get_data(), updated_data)

        # Test adding a different notification name
        other_data = {"message": "different notification"}
        notification3 = r1.add_notification("test2", other_data)
        db.session.commit()

        all_notifications = db.session.scalars(r1.notifications.select()).all()
        self.assertEqual(len(all_notifications), 2)


class TestMessage(unittest.TestCase):
    def setUp(self):
        add_to_index_patch.start()
        remove_from_index_patch.start()
        self.es_patcher = patch(
            "src.app.__init__.Elasticsearch", return_value=MockElasticsearch
        )
        self.mock_es = self.es_patcher.start()
        self.reindex_patcher = patch(
            "src.app.models.searchable.SearchableMixin.reindex", mock_reindex
        )
        self.mock_reindex = self.reindex_patcher.start()
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        self.es_patcher.stop()
        self.reindex_patcher.stop()

    def test_send_message(self):
        # Create two researchers
        sender = Researcher(researcher_name="alice", email="alice@example.com")
        recipient = Researcher(researcher_name="bob", email="bob@example.com")
        db.session.add_all([sender, recipient])
        db.session.commit()

        message = Message(
            author=sender,
            recipient=recipient,
            body="Hello Bob, this is a test message!",
        )
        db.session.add(message)
        db.session.commit()

        # Verify message was created correctly
        self.assertIsNotNone(message.id)
        self.assertEqual(message.sender_id, sender.id)
        self.assertEqual(message.recipient_id, recipient.id)
        self.assertEqual(message.body, "Hello Bob, this is a test message!")
        self.assertIsNotNone(message.timestamp)

        # Verify relationships work correctly
        self.assertEqual(message.author, sender)
        self.assertEqual(message.recipient, recipient)

    def test_unread_message_count(self):
        # Create two researchers
        sender = Researcher(researcher_name="alice", email="alice@example.com")
        recipient = Researcher(researcher_name="bob", email="bob@example.com")
        db.session.add_all([sender, recipient])
        db.session.commit()

        # Initially, recipient should have 0 unread messages
        self.assertEqual(recipient.unread_messages_count(), 0)

        message = Message(author=sender, recipient=recipient, body="First message")
        db.session.add(message)
        db.session.commit()

        # Recipient should now have 1 unread message
        self.assertEqual(recipient.unread_messages_count(), 1)

        # Send another message
        message2 = Message(author=sender, recipient=recipient, body="Second message")
        db.session.add(message2)
        db.session.commit()

        # Recipient should now have 2 unread messages
        self.assertEqual(recipient.unread_messages_count(), 2)

        recipient.last_message_read_time = datetime.now(timezone.utc)
        db.session.commit()

        # Should now have 0 unread messages
        self.assertEqual(recipient.unread_messages_count(), 0)

    def test_message_notification(self):
        """Test that sending a message creates a notification"""
        # Create two researchers
        sender = Researcher(researcher_name="alice", email="alice@example.com")
        recipient = Researcher(researcher_name="bob", email="bob@example.com")
        db.session.add_all([sender, recipient])
        db.session.commit()

        message = Message(author=sender, recipient=recipient, body="Hello Bob!")
        db.session.add(message)
        db.session.commit()

        # Add notification for unread message count
        recipient.add_notification(
            "unread_message_count", recipient.unread_messages_count()
        )
        db.session.commit()

        # Verify notification was created
        notifications = db.session.scalars(
            recipient.notifications.select().where(
                Notification.name == "unread_message_count"
            )
        ).all()
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].get_data(), 1)
