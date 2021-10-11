const csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', function() {
  document.addEventListener('click', event => {
    const element = event.target;

    // Manage "Follow" button actions with JavaScript for better user experience
    if (element.id === 'follow') {
      toggleFollow();
    }

    // Manage "Edit" post link with JavaScript so we don't need to reload entire page
    if (element.className.includes('edit')) {
      const post = findParentPost(element);
      setEdition(post);
    }

    // Manage "Like/Unlike"
    if (element.className.includes('like')) {
      const post = findParentPost(element);
      toggleLike(post);
    }
  })
})

function toggleFollow() {
  const followButton = document.querySelector('#follow');
  const profileUrl = followButton.dataset.profileurl;
  const followerCount = document.querySelector('#follower-count')

  let follow_state = false;
  if (followButton.innerText === 'Follow') {
    follow_state = true;
  }

  console.log(profileUrl)

  fetch(profileUrl, {
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
function setEdition(post) {
  const postUrl = post.dataset.url;
  // Get post content
  const editContainer = post.querySelector('.edit-container');
  const originalPostContent = post.querySelector('.post-text').innerText;

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

    console.log('save', postUrl, newPostContent);
    fetch(postUrl, {
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
        resetEdition(post, newPostContent);
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
    resetEdition(post, originalPostContent);
  }

  // Also cancel edition when pressing 'Escape' on textarea
  const textarea = editContainer.firstElementChild;
  textarea.addEventListener('keyup', event => {
    if (event.key == 'Escape') {
      resetEdition(post, originalPostContent);
    }
  })

  // Set focus to textarea
  editContainer.firstElementChild.focus();
}

// Set post into 'view' mode
function resetEdition(post, postContent) {
  editContainer = post.querySelector('.edit-container');
  editContainer.innerHTML = `<p class="post-text">${postContent}</p>
    <p><a class="edit card-link" href="javascript:;">Edit</a></p>`;
}

function toggleLike(post) {
  postUrl = post.dataset.url;
  likeIcon = post.querySelector('i');
  likeValueStr = likeIcon.className.split(' ')[0];
  likeValue = likeValueStr === 'like' ? true : false;
  likesCount = post.querySelector('.likes-count');

  console.log(likeValueStr, postUrl);
  fetch(postUrl, {
    method: 'PUT',
    headers: {
      'X-CSRFToken': csrftoken
    },
    body: JSON.stringify({
      like: likeValue
    })
  })
  .then(response => {
    if (response.status === 200) {
      // if like value was correctly set, toggle icon
      if (likeValue) {
        likeIcon.className = 'unlike bi bi-heart-fill';
        likeIcon.title = 'Unlike this post';
      } else {
        likeIcon.className = 'like bi bi-heart';
        likeIcon.title = 'Like this post';
      }
    }
    return response.json();
  })
  .then(result => {
    console.log(result);
    // update likes counter if received
    if ('likesCount' in result) {
      likesCount.innerText = result.likesCount
    }
  })
}

function findParentPost(element) {
  while (!element.className.includes('post')) {
    element = element.parentElement;
  }
  return element;
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