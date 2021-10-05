import json
import time

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db.models import Max
from django.test import Client, TestCase
from selenium import webdriver

from .models import User, Post


# Create your tests here.
class NetworkTestCase(TestCase):

    def setUp(self):
        # Create users.
        u1 = User.objects.create(username="user1")
        u2 = User.objects.create(username="user2")
        u3 = User.objects.create(username="user3")

        # Create posts.
        Post.objects.create(author=u1, text="user1 post#1")
        Post.objects.create(author=u1, text="user1 post#2")
        Post.objects.create(author=u2, text="user2 post#1")

        # Assign followers
        u1.followers.add(u2)
        u1.followers.add(u3)

    def test_post(self):
        """Submit new post and check that post counts increases"""
        c = Client()

        # log-in user1
        u1 = User.objects.get(username="user1")
        c.force_login(u1)

        global_post_count_before = Post.objects.count()
        user_post_count_before = u1.posts.count()

        # submit new post
        c.post('/post', {'text': 'test post'})
        self.assertEqual(Post.objects.count(), global_post_count_before + 1)
        self.assertEqual(u1.posts.count(), user_post_count_before + 1)

        # reset
        Post.objects.last().delete()

    def test_index(self):
        """Index page must contain 3 posts in reverse chronological order"""
        c = Client()
        response = c.get("/")
        # print(response)
        self.assertEqual(response.status_code, 200)
        # test number of posts
        self.assertEqual(response.context["posts"].count(), 3)
        # test chronological order of posts
        self.assertGreater(response.context["posts"][0].creation_date, response.context["posts"][1].creation_date)
        self.assertGreater(response.context["posts"][1].creation_date, response.context["posts"][2].creation_date)

    def test_valid_profile_page(self):
        """Check that we get correct profile page for a valid user"""
        u1 = User.objects.get(username="user1")
        c = Client()
        response = c.get(f"/users/{u1.id}")
        # print(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user_"].username, u1.username)

    def test_valid_profile_page_posts(self):
        """Profile page for User1 must contain 2 posts in reverse chronological order"""
        u1 = User.objects.get(username="user1")
        c = Client()
        response = c.get(f"/users/{u1.id}")
        # print(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["posts"].count(), 2)
        self.assertGreater(response.context["posts"][0].creation_date, response.context["posts"][1].creation_date)

    def test_invalid_profile_page(self):
        """Check that we get a 404 (not found) status code for a user with invalid id"""
        max_user_id = User.objects.all().aggregate(Max("id"))["id__max"]
        c = Client()
        response = c.get(f"/users/{max_user_id + 1}")
        # print(response)
        self.assertEqual(response.status_code, 404)

    def test_followers_count(self):
        """Check that user1 have 2 followers"""
        u1 = User.objects.get(username="user1")
        self.assertEqual(u1.followers.count(), 2)

    def test_following_count(self):
        """Check that user2 is following 1 user"""
        u2 = User.objects.get(username="user2")
        self.assertEqual(u2.following.count(), 1)

    def test_follow_unfollow(self):
        """Check that user1 user can follow and unfollow user2"""
        c = Client()

        # log-in user1
        u1 = User.objects.get(username="user1")
        c.force_login(u1)

        u2 = User.objects.get(username="user2")

        # follow user2
        response = c.put(f"/users/{u2.id}/follow", data=json.dumps({'follow': True}))
        # print(response, response.content)

        self.assertEqual(response.status_code, 200)
        self.assertIn(u1, u2.followers.all())
        self.assertIn(u2, u1.following.all())

        # unfollow user2
        response = c.put(f"/users/{u2.id}/follow", data=json.dumps({'follow': False}))
        # print(response, response.content)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(u1, u2.followers.all())
        self.assertNotIn(u2, u1.following.all())


class WebpageTest(StaticLiveServerTestCase):

    # setup from https://docs.djangoproject.com/en/3.2/topics/testing/tools/#liveservertestcase
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = webdriver.Chrome()
        # cls.driver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        # Create users
        User.objects.create_user(username="test_user", password="secret")
        User.objects.create_user(username="user2")

    def test_end_to_end(self):
        """End to end test: Login, Post, Follow"""

        # Log-in test_user
        login_url = self.live_server_url + "/login"
        self.driver.get(login_url)

        username_input = self.driver.find_element_by_name("username")
        username_input.send_keys("test_user")
        password_input = self.driver.find_element_by_name("password")
        password_input.send_keys("secret")
        follow_button = self.driver.find_element_by_class_name("btn")
        follow_button.click()

        # Check that we have been logged into index page
        index_url = self.live_server_url + "/"
        self.assertEqual(self.driver.current_url, index_url)
        self.assertEqual(self.driver.find_element_by_id("username").text, "test_user")

        # Submit new post
        textarea = self.driver.find_element_by_id("id_text")
        textarea.send_keys("Test Post")
        post_button = self.driver.find_element_by_class_name("btn")
        post_button.click()

        # Check that post has been correctly submitted
        last_post = self.driver.find_elements_by_css_selector("#all-posts > div")[0]
        last_post_author = last_post.find_element_by_tag_name("a").text
        last_post_text = last_post.find_element_by_tag_name("p").text
        self.assertEqual(last_post_author, "test_user")
        self.assertEqual(last_post_text, "Test Post")

        # Load user2 profile page
        u2 = User.objects.get(username="user2")
        u2_profile_url = self.live_server_url + f"/users/{u2.id}"
        self.driver.get(u2_profile_url)

        follower_count_span = self.driver.find_element_by_id("follower-count")
        follow_button = self.driver.find_element_by_id("follow")

        # Check initial state of profile page
        self.assertEqual(follow_button.text, "Follow")
        follower_count_initial = int(follower_count_span.text)
        self.assertEqual(follower_count_initial, 0)

        # "Follow"
        follow_button.click()
        time.sleep(0.1)
        self.assertEqual(follow_button.text, "Unfollow")
        self.assertEqual(int(follower_count_span.text), follower_count_initial + 1)

        # "Unfollow"
        follow_button.click()
        time.sleep(0.1)
        self.assertEqual(follow_button.text, "Follow")
        self.assertEqual(int(follower_count_span.text), follower_count_initial)
