import json
import time

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.db.models import Max
from django.test import Client, TestCase
from django.urls import reverse
from selenium import webdriver
from bs4 import BeautifulSoup


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
        c.post(reverse("create_post"), {'text': 'test post'})
        self.assertEqual(Post.objects.count(), global_post_count_initial + 1)
        self.assertEqual(u1.posts.count(), user_post_count_initial + 1)

        # reset
        Post.objects.last().delete()

    def test_post_not_authenticated(self):
        """Check that for a not authenticated user, there's no post form in 'All Posts' page"""
        c = Client()
        response = c.get(reverse("index"))
        self.assertNotContains(response, "new-post-form")

    def test_index(self):
        """Index page must contain 3 posts in reverse chronological order"""
        c = Client()
        response = c.get(reverse("index"))
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
        index_url = reverse("index")
        # 1st page must contain 10 posts
        response = c.get(index_url)
        self.assertEqual(len(response.context["posts_page"].object_list), 10)

        # 2nd page must contain 1 post
        response = c.get(f"{index_url}?page=2")
        self.assertEqual(len(response.context["posts_page"].object_list), 1)

    def test_profile_page(self):
        """Check profile page for a valid user:
        - Followers and following count
        - Post count and reverse chronological order"""
        u1 = User.objects.get(username="user1")

        # Get user1 profile page
        c = Client()
        response = c.get(reverse("profile", args=[u1.id]))
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
        profile_url = reverse("profile", args=[max_user_id + 1])
        response = c.get(profile_url)
        self.assertEqual(response.status_code, 404)

    def test_profile_page_pagination(self):
        """Profile page must contain maximum 10 posts per page"""
        u3 = User.objects.get(username="user3")

        # Create 11 posts for user3
        for i in range(1, 12):
            Post.objects.create(author=u3, text=f"user3 post#{i}")

        c = Client()
        # 1st page must contain 10 posts
        u3_profile_url = reverse("profile", args=[u3.id])
        response = c.get(u3_profile_url)
        self.assertEqual(len(response.context["posts_page"].object_list), 10)

        # 2nd page must contain 1 post
        response = c.get(f"{u3_profile_url}?page=2")
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
        u3_url = reverse("profile", args=[u3.id])
        response = c.put(u3_url, data=json.dumps({'follow': True}))

        self.assertEqual(response.status_code, 200)
        self.assertIn(u1, u3.followers.all())
        self.assertIn(u3, u1.following.all())
        self.assertEqual(u3.followers.count(), 1)

        # unfollow user3
        response = c.put(u3_url, data=json.dumps({'follow': False}))

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
        response = c.get(reverse("profile", args=[u1.id]))
        self.assertEqual(response.status_code, 200)

        # 'Follow' button must not be present
        self.assertNotContains(response, "id=\"follow\"")

        # Request to follow user1
        u1_profile = reverse("profile", args=[u1.id])
        response = c.put(u1_profile, data=json.dumps({'follow': True}))
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
        u1_profile = reverse("profile", args=[u1.id])
        response = c.get(u1_profile)
        self.assertEqual(response.status_code, 200)

        # 'Follow' button must not be present
        self.assertNotContains(response, "id=\"follow\"")

        # Request to follow user1
        response = c.put(u1_profile, data=json.dumps({'follow': True}))
        self.assertEqual(response.status_code, 400)

    def test_following_page(self):
        """Following page for user2 must contain the posts from user1, in reverse chronological order"""
        u2 = User.objects.get(username="user2")

        # log-in user2
        c = Client()
        c.force_login(u2)

        response = c.get(reverse("following"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["posts_page"].object_list), 2)
        self.assertGreater(response.context["posts_page"][0].creation_date,
                           response.context["posts_page"][1].creation_date)

    def test_following_page_not_authenticated(self):
        """For a not authenticated user, check that:
        - 'Following' link is not available
        - When trying to access 'Following' page, user is redirected to login page"""
        c = Client()
        response = c.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Following")

        following_url = reverse("following")
        login_url = reverse("login")
        response = c.get(following_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{login_url}?next={following_url}")

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

        following_url = reverse("following")
        # 1st page must contain 10 posts
        response = c.get(following_url)
        self.assertEqual(len(response.context["posts_page"].object_list), 10)

        # 2nd page must contain 1 post
        response = c.get(f"{following_url}?page=2")
        self.assertEqual(len(response.context["posts_page"].object_list), 1)

    def test_edit_post(self):
        """Check that user1 can update content of one of its posts"""
        u1 = User.objects.get(username="user1")

        # log-in user1
        c = Client()
        c.force_login(u1)

        # Update content of user's last post
        post_id = u1.posts.last().id
        post_url = reverse("update_post", args=[post_id])
        response = c.put(post_url, data=json.dumps({'content': 'content updated'}))

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
        post_url = reverse("update_post", args=[post_id])
        response = c.put(post_url, data=json.dumps({'content': 'content updated'}))

        self.assertEqual(response.status_code, 403)

    def test_edit_invalid_post(self):
        """Check that we get a 404 (not found) status code when trying to edit a post with invalid id"""
        u1 = User.objects.get(username="user1")

        # log-in user1
        c = Client()
        c.force_login(u1)

        max_post_id = Post.objects.all().aggregate(Max("id"))["id__max"]
        post_url = reverse("update_post", args=[max_post_id + 1])
        response = c.put(post_url, data=json.dumps({'content': 'content updated'}))
        self.assertEqual(response.status_code, 404)

    def test_edit_link_presence(self):
        """For a not authenticated user, no post must has an 'Edit' link.
        For an authenticated user, 'Edit' link must be present on all of its posts and absent on other user's posts"""
        u1 = User.objects.get(username="user1")
        u2 = User.objects.get(username="user2")

        # Load 'All Posts' page
        c = Client()
        response = c.get(reverse("index"))
        soup = BeautifulSoup(response.content, "html.parser")

        # No post must have an 'Edit' link (as no user is authenticated)
        posts = soup.find_all("div", class_="post")
        for post in posts:
            edit_link = post.find("a", class_="edit")
            self.assertIsNone(edit_link)

        # Log-in user1
        c.force_login(u1)

        # Load 'All Posts' page
        response = c.get(reverse("index"))
        soup = BeautifulSoup(response.content, "html.parser")

        # All user1 posts must have an 'Edit' link. Posts from other users not.
        posts = soup.find_all("div", class_="post")
        for post in posts:
            author = post.find("h2").text
            edit_link = post.find("a", class_="edit")
            if author == "user1":
                self.assertIsNotNone(edit_link)
            else:
                self.assertIsNone(edit_link)

        # Load user1 'Profile' page
        response = c.get(reverse("profile", args=[u1.id]))
        soup = BeautifulSoup(response.content, "html.parser")

        # All posts must have an 'Edit' link
        posts = soup.find_all("div", class_="post")
        for post in posts:
            edit_link = post.find("a", class_="edit")
            self.assertIsNotNone(edit_link)

        # Load user2 'Profile' page
        response = c.get(reverse("profile", args=[u2.id]))
        soup = BeautifulSoup(response.content, "html.parser")

        # No 'edit' link must be present
        posts = soup.find_all("div", class_="post")
        for post in posts:
            edit_link = post.find("a", class_="edit")
            self.assertIsNone(edit_link)

    def test_like_unlike(self):
        """Check that a user can like any post"""
        u1 = User.objects.get(username="user1")
        u2 = User.objects.get(username="user2")

        # log-in user1
        c = Client()
        c.force_login(u1)

        # user2 last post like count initial state
        post = u2.posts.last()
        self.assertEqual(post.likes_count, 0)

        # like post
        post_url = reverse("update_post", args=[post.id])
        response = c.put(post_url, data=json.dumps({'like': True}))

        self.assertEqual(response.status_code, 200)
        self.assertIn(u1, post.liked_by.all())
        self.assertEqual(post.likes_count, 1)

        # unlike post
        response = c.put(post_url, data=json.dumps({'like': False}))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(u1, post.liked_by.all())
        self.assertEqual(post.likes_count, 0)

        # like self last post
        post = u1.posts.last()
        response = c.put(reverse("update_post", args=[post.id]), data=json.dumps({'like': True}))

        self.assertEqual(response.status_code, 200)
        self.assertIn(u1, post.liked_by.all())
        self.assertEqual(post.likes_count, 1)

    def test_like_not_authenticated(self):
        """Test that a not authenticated user must have a 'forbidden' response when trying to like a post"""
        u1 = User.objects.get(username="user1")

        post = u1.posts.last()
        post_like_count_initial = post.likes_count

        # Send request to like post
        c = Client()
        response = c.put(reverse("update_post", args=[post.id]), data=json.dumps({'like': True}))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(post.likes_count, post_like_count_initial)


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
        u2 = User.objects.create_user(username="user2")

        # Add post
        Post.objects.create(author=u2, text="user2 post")

    def test_end_to_end(self):
        """End to end test: Login, Post, Edit, Follow, Like"""
        index_url = self.live_server_url + reverse("index")
        login_url = self.live_server_url + reverse("login")
        following_url = self.live_server_url + reverse("following")
        u2 = User.objects.get(username="user2")
        u2_profile_url = self.live_server_url + reverse("profile", args=[u2.id])
        test_user = User.objects.get(username="test_user")

        # Check that not-authenticated user can't like posts in 'All Posts' and 'Profile' pages
        for url in [index_url, u2_profile_url]:
            self.driver.get(url)
            last_post = self.driver.find_elements_by_class_name("post")[0]
            like_count_before = int(last_post.find_element_by_class_name("likes-count").text)
            like_icon = last_post.find_element_by_tag_name("i")
            like_icon.click()
            like_count_after = int(last_post.find_element_by_class_name("likes-count").text)
            self.assertEqual(like_count_after, like_count_before)

        # Log-in test_user
        self.driver.get(login_url)

        username_input = self.driver.find_element_by_name("username")
        username_input.send_keys("test_user")
        password_input = self.driver.find_element_by_name("password")
        password_input.send_keys("secret")
        follow_button = self.driver.find_element_by_class_name("btn")
        follow_button.click()

        # Check that we have been logged into index page
        self.assertEqual(self.driver.current_url, index_url)
        self.assertEqual(self.driver.find_element_by_id("username").text, "test_user")

        # Check that 'All Posts' link take to index page
        self.driver.find_element_by_link_text("All Posts").click()
        self.assertEqual(self.driver.current_url, index_url)

        # Submit new post
        new_post_textarea = self.driver.find_element_by_id("id_text")
        new_post_textarea.send_keys("Test Post")
        post_button = self.driver.find_element_by_css_selector("input[value='Post']")
        post_button.click()

        # Check that post has been correctly submitted
        last_post = self.driver.find_elements_by_class_name("post")[0]
        last_post_author = last_post.find_element_by_css_selector("h2 > a").text
        last_post_text = last_post.find_element_by_class_name("post-text").text
        self.assertEqual(last_post_author, "test_user")
        self.assertEqual(last_post_text, "Test Post")

        # Check that clicking on 'Edit' link loads a textarea without reloading the page
        edit_link = last_post.find_element_by_link_text("Edit")
        edit_link.click()
        # if the page has been reloaded last_post would no longer exist
        edit_textarea = last_post.find_element_by_tag_name("textarea")
        self.assertIsNotNone(edit_textarea)

        # Cancel edition
        edit_textarea.clear()
        cancel_button = last_post.find_element_by_class_name("cancel")
        cancel_button.click()
        # Check that post text has not changed
        last_post_text = last_post.find_element_by_class_name("post-text").text
        self.assertEqual(last_post_text, "Test Post")

        # Edit post
        edit_link = last_post.find_element_by_link_text("Edit")
        edit_link.click()
        edit_textarea = last_post.find_element_by_tag_name("textarea")
        edit_textarea.clear()
        edit_textarea.send_keys("Test Post (edited)")
        save_button = last_post.find_element_by_class_name("save")
        save_button.click()
        time.sleep(0.1)

        # Check that post content has been updated
        last_post_text = last_post.find_element_by_class_name("post-text").text
        self.assertEqual(last_post_author, "test_user")
        self.assertEqual(last_post_text, "Test Post (edited)")

        # Like/Unlike ('All Posts' page)
        posts = self.driver.find_elements_by_class_name("post")
        for post in posts:
            post_id = int(post.get_attribute("data-url").split("/")[-1])
            # Check initial state of like icon and count ('All Posts' page)
            like_count_initial = int(post.find_element_by_class_name("likes-count").text)
            self.assertEqual(like_count_initial, 0)
            like_icon = post.find_element_by_tag_name("i")
            like_icon_class = like_icon.get_attribute("class").split(" ")[-1]
            self.assertEqual(like_icon_class, "bi-heart")

            # Like
            like_icon.click()
            time.sleep(0.1)
            # Check that count is updated without reloading page (if page reloads, post wouldn't be attached)
            like_count = int(post.find_element_by_class_name("likes-count").text)
            self.assertEqual(like_count, like_count_initial + 1)
            # Check icon was toggled
            like_icon_class = like_icon.get_attribute("class").split(" ")[-1]
            self.assertEqual(like_icon_class, "bi-heart-fill")
            self.assertIn(test_user, Post.objects.get(id=post_id).liked_by.all())

            # Unlike
            like_icon.click()
            time.sleep(0.1)
            like_count = int(post.find_element_by_class_name("likes-count").text)
            self.assertEqual(like_count, like_count_initial)
            like_icon_class = like_icon.get_attribute("class").split(" ")[-1]
            self.assertEqual(like_icon_class, "bi-heart")
            self.assertNotIn(test_user, Post.objects.get(id=post_id).liked_by.all())

        # Click on user2 username to load profile page
        self.driver.find_element_by_link_text("user2").click()

        # Check that the correct profile has been loaded
        self.assertEqual(self.driver.current_url, u2_profile_url)

        # Check initial state of profile page
        follow_button = self.driver.find_element_by_id("follow")
        self.assertEqual(follow_button.text, "Follow")
        follower_count_span = self.driver.find_element_by_id("follower-count")
        follower_count_initial = int(follower_count_span.text)
        self.assertEqual(follower_count_initial, 0)
        posts = self.driver.find_elements_by_class_name("post")
        self.assertEqual(len(posts), 1)

        # "Follow"
        follow_button.click()
        time.sleep(0.1)
        follower_count = int(follower_count_span.text)
        self.assertEqual(follow_button.text, "Unfollow")
        self.assertEqual(follower_count, follower_count_initial + 1)

        # "Unfollow"
        follow_button.click()
        time.sleep(0.1)
        follower_count = int(follower_count_span.text)
        self.assertEqual(follow_button.text, "Follow")
        self.assertEqual(follower_count, follower_count_initial)

        # Like (Profile page)
        post = self.driver.find_element_by_class_name("post")
        post_id = int(post.get_attribute("data-url").split("/")[-1])
        # Post initial status
        like_count_initial = int(post.find_element_by_class_name("likes-count").text)
        self.assertEqual(like_count_initial, 0)
        like_icon = post.find_element_by_tag_name("i")
        like_icon_class = like_icon.get_attribute("class").split(" ")[-1]
        self.assertEqual(like_icon_class, "bi-heart")
        # Like the post
        like_icon.click()
        time.sleep(0.1)
        like_count = int(post.find_element_by_class_name("likes-count").text)
        self.assertEqual(like_count, like_count_initial + 1)
        like_icon_class = like_icon.get_attribute("class").split(" ")[-1]
        self.assertEqual(like_icon_class, "bi-heart-fill")
        self.assertIn(test_user, Post.objects.get(id=post_id).liked_by.all())

        # Check that 'Following' link takes to Following page
        self.driver.find_element_by_link_text("Following").click()
        self.assertEqual(self.driver.current_url, following_url)
