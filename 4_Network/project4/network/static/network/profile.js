document.addEventListener('DOMContentLoaded', function() {
  // manage "Follow" button actions with JavaScript for better user experience
  document.querySelector('#follow').onclick = (event) => {
    const button = event.target;
    const userId = button.dataset.userid;
    const csrftoken = getCookie('csrftoken');
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
