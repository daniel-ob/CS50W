const csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', function() {
  document.addEventListener('click', event => {
    const element = event.target;

    // Manage "Follow" button actions with JavaScript for better user experience
    if (element.id == 'follow') {
      toggleFollow();
    }

    // Manage "Edit" post link with JavaScript so we don't need to reload entire page
    if (element.className == 'edit') {
      const editContainer = element.parentElement;
      setEdition(editContainer);
    }
  })
})

function toggleFollow() {
  const followButton = document.querySelector('#follow');
  const userId = followButton.dataset.userid;
  const followerCount = document.querySelector('#follower-count')

  let follow_state = false;
  if (followButton.innerText === 'Follow') {
    follow_state = true;
  }

  fetch(`/users/${userId}`, {
    method: 'PUT',
    headers: {
      'X-CSRFToken': csrftoken
    },
    body: JSON.stringify({
      follow: follow_state
    })
  })
  .then(response => {
    if (response.status === 200) {
      // if follow status was correctly set, toggle button
      if (follow_state) {
        followButton.innerText = 'Unfollow';
        followButton.className = 'btn btn-sm btn-outline-primary ml-2';
      } else {
        followButton.innerText = 'Follow';
        followButton.className = 'btn btn-sm btn-primary ml-2';
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

// Set post into 'edition' mode
function setEdition(editContainer) {
  const postId = editContainer.dataset['postid'];

  // Get post content
  const originalPostContent = editContainer.firstElementChild.innerText;

  // Add textarea with post content
  editContainer.innerHTML = `<textarea class="form-control" cols="40" rows="2" maxlength="512" required="">${originalPostContent}</textarea>`

  // Add button to Save the edited post
  const saveButton = document.createElement('button');
  saveButton.innerText = 'Save';
  saveButton.className = 'save btn btn-primary my-2';
  editContainer.append(saveButton);

  // Set action for Save button
  saveButton.onclick = () => {
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
        resetEdition(editContainer, newPostContent);
      }
    })
  }

  // Add button to Cancel edition
  const cancelButton = document.createElement('button');
  cancelButton.innerText = 'Cancel';
  cancelButton.className = 'cancel btn btn-secondary m-2';
  editContainer.append(cancelButton);

  // Set action for Cancel button
  cancelButton.onclick = () => {
    // Switch edit container to 'view' mode with original post content
    resetEdition(editContainer, originalPostContent);
  }

  // Also cancel edition when pressing 'Escape' on textarea
  const textarea = editContainer.firstElementChild;
  textarea.addEventListener('keyup', event => {
    if (event.key == 'Escape') {
      resetEdition(editContainer, originalPostContent);
    }
  })

  // Set focus to textarea
  editContainer.firstElementChild.focus();
}

// Set post into 'view' mode
function resetEdition(editContainer, postContent) {
  editContainer.innerHTML = `<p class="post-text">${postContent}</p>
    <a class="edit" href="javascript:;">Edit</a>`;
}

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