document.addEventListener('DOMContentLoaded', function() {

  document.addEventListener('click', event => {
    const element = event.target;
    const csrftoken = getCookie('csrftoken');

    // Manage "Follow" button actions with JavaScript for better user experience
    if (element.id == 'follow') {
      const button = element;
      const userId = button.dataset.userid;
      const followerCount = document.querySelector('#follower-count')

      let follow = false;
      if (button.innerText === 'Follow') {
        follow = true;
      }

      fetch(`/users/${userId}`, {
        method: 'PUT',
        headers: {
          'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
          follow: follow
        })
      })
      .then(response => {
        if (response.status === 200) {
          // if follow status was correctly set, toggle button
          if (follow) {
            button.innerText = 'Unfollow';
            button.className = 'btn btn-sm btn-outline-primary ml-2';
          } else {
            button.innerText = 'Follow';
            button.className = 'btn btn-sm btn-primary ml-2';
          }
        }
        return response.json();
      })
      .then(result => {
        console.log(result);
        // update follower counter if received
        if ('followerCount' in result) {
          followerCount.innerText = result.followerCount
        }
      })
    }

    // Manage "Edit" post link with JavaScript so we don't need to reload entire page
    if (element.className == 'edit') {
      const editContainer = element.parentElement;
      const postId = editContainer.dataset['postid'];

      // Get post content
      const originalPostContent = editContainer.firstElementChild.innerText;

      // Empty edit container
      editContainer.innerHTML = '';

      // Add textarea with post content
      editContainer.innerHTML = `<textarea class="form-control" cols="40" rows="2" maxlength="512" required="">${originalPostContent}</textarea>`

      // Add button to Save the edited post
      const saveButton = document.createElement('button');
      saveButton.innerText = 'Save';
      saveButton.className = 'save btn btn-primary my-2';
      editContainer.append(saveButton);

      // Set focus to textarea
      editContainer.firstElementChild.focus();

      // Set action for Save button
      saveButton.onclick = event => {
        const thisSaveButton = event.target;
        const editContainer = thisSaveButton.parentElement;
        const postId = editContainer.dataset['postid'];
        const newPostContent = editContainer.firstElementChild.value;

        console.log('save', postId, newPostContent);
        fetch(`/posts/${postId}`, {
          method: 'PUT',
          headers: {
            'X-CSRFToken': csrftoken
          },
          body: JSON.stringify({
              content: newPostContent
          })
        })
        .then(response => response.json())
        .then(result => {
          console.log(result);
          if (!result.error) {
            // Reset edit container
            editContainer.innerHTML = `<p class="post-text">${newPostContent}</p>
              <a class="edit" data-postid="${postId}" href="javascript:;">Edit</a>`
          }
        })
      }
    }
  })
})

// from https://docs.djangoproject.com/en/3.2/ref/csrf/
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}