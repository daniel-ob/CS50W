import json
import time

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db.models import Max
from django.test import Client, TestCase
from selenium import webdriver

from .models import User, Post


class NetworkTestCase(TestCase):

    def setUp(self):
        # Create users
        u1 = User.objects.create(username="user1")
        u2 = User.objects.create(username="user2")
        u3 = User.objects.create(username="user3")

        # Create posts
        Post.objects.create(author=u1, text="user1 post#1")
        Post.objects.create(author=u1, text="user1 post#2")
        Post.objects.create(author=u2, text="user2 post#1")

        # Assign followers
        u1.followers.add(u2)
        u1.followers.add(u3)
        u2.followers.add(u1)

    def test_post(self):
        """Submit new post and check that post counts increases"""
        u1 = User.objects.get(username="user1")

        global_post_count_initial = Post.objects.count()
        user_post_count_initial = u1.posts.count()

        # log-in user1
        c = Client()
        c.force_login(u1)

        # submit new post
        c.post('/posts', {'text': 'test post'})
        self.assertEqual(Post.objects.count(), global_post_count_initial + 1)
        self.assertEqual(u1.posts.count(), user_post_count_initial + 1)

        # reset
        Post.objects.last().delete()

    def test_post_not_authenticated(self):
        """Check that for a not authenticated user, there's no post form in 'All Posts' page"""
        c = Client()
        response = c.get("/")
        self.assertNotContains(response, "new-post-form")

    def test_index(self):
        """Index page must contain 3 posts in reverse chronological order"""
        c = Client()
        response = c.get("/")
        self.assertEqual(response.status_code, 200)
        # Check post count
        self.assertEqual(len(response.context["posts_page"].object_list), 3)
        # Check reverse chronological order of posts
        self.assertGreater(response.context["posts_page"][0].creation_date,
                           response.context["posts_page"][1].creation_date)
        self.assertGreater(response.context["posts_page"][1].creation_date,
                           response.context["posts_page"][2].creation_date)

    def test_index_pagination(self):
        """Index page must contain maximum 10 posts per page"""
        u3 = User.objects.get(username="user3")

        # Create 8 posts so that in total there are 11 (3 already exist from setUp())
        for i in range(1, 9):
            Post.objects.create(author=u3, text=f"user3 post#{i}")

        c = Client()
        # 1st page must contain 10 posts
        response = c.get("/")
        self.assertEqual(len(response.context["posts_page"].object_list), 10)

        # 2nd page must contain 1 post
        response = c.get("/?page=2")
        self.assertEqual(len(response.context["posts_page"].object_list), 1)

    def test_profile_page(self):
        """Check profile page for a valid user:
        - Followers and following count
        - Post count and reverse chronological order"""
        u1 = User.objects.get(username="user1")

        # Get user1 profile page
        c = Client()
        response = c.get(f"/users/{u1.id}")
        self.assertEqual(response.status_code, 200)

        # Check that we get the correct profile
        self.assertEqual(response.context["profile_user"].username, u1.username)

        # Check followers and following count
        self.assertEqual(response.context["profile_user"].followers.count(), 2)
        self.assertEqual(response.context["profile_user"].following.count(), 1)

        # Check post count and reverse chronological order
        self.assertEqual(len(response.context["posts_page"]), 2)
        self.assertGreater(response.context["posts_page"][0].creation_date,
                           response.context["posts_page"][1].creation_date)

    def test_invalid_profile_page(self):
        """Check that we get a 404 (not found) status code for a user with invalid id"""
        max_user_id = User.objects.all().aggregate(Max("id"))["id__max"]

        c = Client()
        response = c.get(f"/users/{max_user_id + 1}")
        self.assertEqual(response.status_code, 404)

    def test_profile_page_pagination(self):
        """Profile page must contain maximum 10 posts per page"""
        u3 = User.objects.get(username="user3")

        # Create 11 posts for user3
        for i in range(1, 12):
            Post.objects.create(author=u3, text=f"user3 post#{i}")

        c = Client()
        # 1st page must contain 10 posts
        response = c.get(f"/users/{u3.id}")
        self.assertEqual(len(response.context["posts_page"].object_list), 10)

        # 2nd page must contain 1 post
        response = c.get(f"/users/{u3.id}?page=2")
        self.assertEqual(len(response.context["posts_page"].object_list), 1)

    def test_follow_unfollow(self):
        """Check that user1 user can follow and unfollow user2"""
        u1 = User.objects.get(username="user1")
        u3 = User.objects.get(username="user3")

        # log-in user1
        c = Client()
        c.force_login(u1)

        # user3 initial follower count
        self.assertEqual(u3.followers.count(), 0)

        # follow user3
        response = c.put(f"/users/{u3.id}", data=json.dumps({'follow': True}))

        self.assertEqual(response.status_code, 200)
        self.assertIn(u1, u3.followers.all())
        self.assertIn(u3, u1.following.all())
        self.assertEqual(u3.followers.count(), 1)

        # unfollow user3
        response = c.put(f"/users/{u3.id}", data=json.dumps({'follow': False}))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(u1, u3.followers.all())
        self.assertNotIn(u3, u1.following.all())
        self.assertEqual(u3.followers.count(), 0)

    def test_follow_not_authenticated(self):
        """For a not authenticated user, check that:
        - There's no 'Follow' button on a profile page
        - Follow request obtains a 'forbidden' response"""
        u1 = User.objects.get(username="user1")

        # Load user1 profile
        c = Client()
        response = c.get(f"/users/{u1.id}")
        self.assertEqual(response.status_code, 200)

        # 'Follow' button must not be present
        self.assertNotContains(response, "id=\"follow\"")

        # Request to follow user1
        response = c.put(f"/users/{u1.id}", data=json.dumps({'follow': True}))
        self.assertEqual(response.status_code, 403)

    def test_follow_self(self):
        """Check that a user can't follow himself:
        - There's no 'Follow' button in its own profile page
        - Follow request obtains a '400' response"""
        u1 = User.objects.get(username="user1")

        # Log-in user1
        c = Client()
        c.force_login(u1)

        # Load user1 profile
        response = c.get(f"/users/{u1.id}")
        self.assertEqual(response.status_code, 200)

        # 'Follow' button must not be present
        self.assertNotContains(response, "id=\"follow\"")

        # Request to follow user1
        response = c.put(f"/users/{u1.id}", data=json.dumps({'follow': True}))
        self.assertEqual(response.status_code, 400)

    def test_following_page(self):
        """Following page for user2 must contain the posts from user1, in reverse chronological order"""
        u2 = User.objects.get(username="user2")

        # log-in user2
        c = Client()
        c.force_login(u2)

        response = c.get("/following")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["posts_page"].object_list), 2)
        self.assertGreater(response.context["posts_page"][0].creation_date,
                           response.context["posts_page"][1].creation_date)

    def test_following_page_not_authenticated(self):
        """For a not authenticated user, check that:
        - 'Following' link is not available
        - When trying to access 'Following' page, user is redirected to login page"""
        c = Client()
        response = c.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Following")

        response = c.get("/following")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/login?next=/following")

    def test_following_page_pagination(self):
        """Following page must contain maximum 10 posts per page"""
        u1 = User.objects.get(username="user1")

        # user1 has already 2 posts, create 9 more so that in total there are 11
        for i in range(3, 12):
            Post.objects.create(author=u1, text=f"user1 post#{i}")

        # log-in user2 (that follows only user1)
        c = Client()
        u2 = User.objects.get(username="user2")
        c.force_login(u2)

        # 1st page must contain 10 posts
        response = c.get("/following")
        self.assertEqual(len(response.context["posts_page"].object_list), 10)

        # 2nd page must contain 1 post
        response = c.get("/following?page=2")
        self.assertEqual(len(response.context["posts_page"].object_list), 1)

    def test_edit_post(self):
        """Check that user1 can update content of one of its posts"""
        u1 = User.objects.get(username="user1")

        # log-in user1
        c = Client()
        c.force_login(u1)

        # Update content of user's last post
        post_id = u1.posts.last().id
        response = c.put(f"/posts/{post_id}", data=json.dumps({'content': 'content updated'}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.get(id=post_id).text, "content updated")

    def test_edit_another_user_post(self):
        """Check that user1 can't update content of user2 post"""
        u1 = User.objects.get(username="user1")
        u2 = User.objects.get(username="user2")

        # log-in user1
        c = Client()
        c.force_login(u1)

        # Update post content
        post_id = u2.posts.last().id
        response = c.put(f"/posts/{post_id}", data=json.dumps({'content': 'content updated'}))

        self.assertEqual(response.status_code, 403)

    def test_edit_invalid_post(self):
        """Check that we get a 404 (not found) status code when trying to edit a post with invalid id"""
        u1 = User.objects.get(username="user1")

        # log-in user1
        c = Client()
        c.force_login(u1)

        max_post_id = Post.objects.all().aggregate(Max("id"))["id__max"]
        response = c.put(f"/posts/{max_post_id + 1}", data=json.dumps({'content': 'content updated'}))
        self.assertEqual(response.status_code, 404)


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

        # Add post
        u2 = User.objects.get(username="user2")
        Post.objects.create(author=u2, text="user2 post")

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

        # Check that 'All Posts' link take to index page
        self.driver.find_element_by_link_text("All Posts").click()
        self.assertEqual(self.driver.current_url, index_url)

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

        # Click on user2 username to load profile page
        self.driver.find_element_by_link_text("user2").click()
        u2 = User.objects.get(username="user2")
        u2_profile_url = self.live_server_url + f"/users/{u2.id}"
        self.assertEqual(self.driver.current_url, u2_profile_url)

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

        # Check that 'Following' link takes to Following page
        self.driver.find_element_by_link_text("Following").click()
        following_url = self.live_server_url + "/following"
        self.assertEqual(self.driver.current_url, following_url)
