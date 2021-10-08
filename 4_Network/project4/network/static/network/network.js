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

      // Switch edit container to 'edit' mode.
      // Add textarea with post content
      editContainer.innerHTML = `<textarea class="form-control" cols="40" rows="2" maxlength="512" required="">${originalPostContent}</textarea>`

      // Add button to Save the edited post
      const saveButton = document.createElement('button');
      saveButton.innerText = 'Save';
      saveButton.className = 'save btn btn-primary my-2';
      editContainer.append(saveButton);

      // Set action for Save button
      saveButton.onclick = event => {
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
            // Switch edit container to 'view' mode with new post content
            resetEditContainer(editContainer, newPostContent);
          }
        })
      }

      // Add button to Cancel edition
      const cancelButton = document.createElement('button');
      cancelButton.innerText = 'Cancel';
      cancelButton.className = 'cancel btn btn-secondary m-2';
      editContainer.append(cancelButton);

      // Set action for Cancel button
      cancelButton.onclick = event => {
        // Switch edit container to 'view' mode with original post content
        resetEditContainer(editContainer, originalPostContent);
      }

      // Also cancel edition when pressing 'Escape' on textarea
      const textarea = editContainer.firstElementChild;
      textarea.addEventListener('keyup', event => {
        if (event.key == 'Escape') {
          resetEditContainer(editContainer, originalPostContent);
        }
      })

      // Set focus to textarea
      editContainer.firstElementChild.focus();

      function resetEditContainer(editContainer, postContent) {
        // Reset edit container in 'view mode'
        editContainer.innerHTML = `<p class="post-text">${postContent}</p>
          <a class="edit" href="javascript:;">Edit</a>`;
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