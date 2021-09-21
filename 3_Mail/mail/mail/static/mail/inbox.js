document.addEventListener('DOMContentLoaded', function() {

  // Use buttons to toggle between views
  document.querySelector('#inbox').addEventListener('click', () => load_mailbox('inbox'));
  document.querySelector('#sent').addEventListener('click', () => load_mailbox('sent'));
  document.querySelector('#archived').addEventListener('click', () => load_mailbox('archived'));
  document.querySelector('#compose').addEventListener('click', () => compose_email());

  // By default, load the inbox
  load_mailbox('inbox');
});

function compose_email() {

  // Update nav bar
  update_nav('compose');

  // Show compose view and hide other views
  document.querySelector('#emails-view').style.display = 'none';
  document.querySelector('#email-view').style.display = 'none';
  document.querySelector('#compose-view').style.display = 'block';

  // Clear out composition fields
  document.querySelector('#compose-recipients').value = '';
  document.querySelector('#compose-subject').value = '';
  document.querySelector('#compose-body').value = '';

  // Clear errors
  document.querySelector('#error').innerHTML = '';
  document.querySelector('#recipients-error').innerHTML = '';
  document.querySelector('#compose-recipients').addEventListener('input', () => {
    document.querySelector('#recipients-error').innerHTML = '';
  });

  // Send email at form submission
  document.querySelector('#compose-form').onsubmit = send_email;
}

function load_mailbox(mailbox) {

  // Update nav bar (nav-link id matches mailbox name)
  update_nav(mailbox);

  // Show the mailbox and hide other views
  document.querySelector('#emails-view').style.display = 'block';
  document.querySelector('#email-view').style.display = 'none';
  document.querySelector('#compose-view').style.display = 'none';

  // Clear error
  document.querySelector('#error').innerHTML = '';

  // Clear email-container
  document.querySelector('#email-container').innerHTML = '';

  // Get mailbox url (set dynamically into dataset by back-end)
  const re = /^.*\//;
  const baseUrl = re.exec(document.querySelector('#emails-view').dataset.url)[0];
  url = baseUrl + mailbox

  // Get emails
  fetch(url)
  .then(response => response.json())
  .then(emails => {
    // If emails on mailbox
    if (emails.length > 0) {
      // Print emails
      console.log(emails);

      // Create one row <div> per email (using Bootstrap grid)
      emails.forEach(email => {
        const row = document.createElement('div');
        const recipients = document.createElement('div');
        const sender = document.createElement('div');
        const subject = document.createElement('div');
        const timestamp = document.createElement('div');

        // Set styles
        row.className = 'row border p-2';
        if (email.read === false) {
          row.className += ' bg-white';
        } else {
          row.className += ' bg-light';
        }
        recipients.className = 'col-sm-3 font-weight-bold text-break';
        sender.className = 'col-sm-3 font-weight-bold text-break';
        subject.className = 'col-sm-6';
        timestamp.className = 'col-sm-3 text-right';

        // Set email details
        recipients.innerHTML = 'To: ' + email.recipients;
        sender.innerHTML = email.sender;
        subject.innerHTML = email.subject;
        timestamp.innerHTML = email.timestamp;

        // Show sender or recipients address depending on mailbox
        if (mailbox === 'sent') {
          row.append(recipients)
        } else {
          row.append(sender);
        }
        row.append(subject);
        row.append(timestamp);

        // Add email to container
        document.querySelector('#email-container').append(row);

        // Open the email when user clicks on it
        row.addEventListener('click', () => view_email(email.id, mailbox));
      });
    } else {
      // If no emails in mailbox, display an 'empty' message
      const message = document.createElement('p');
      message.innerHTML = 'Mailbox empty';
      document.querySelector('#email-container').append(message);
    }
  })
  .catch(error => show_error(error));
}

function view_email(id, mailbox) {

  // Update nav bar (deactivate all)
  update_nav();

  // Show email view and hide other views
  document.querySelector('#emails-view').style.display = 'none';
  document.querySelector('#email-view').style.display = 'block';
  document.querySelector('#compose-view').style.display = 'none';

  // Get the email
  fetch(get_email_url(id))
  .then(response => response.json())
  .then(email => {
    // Print email
    console.log(email);

    // Show email details
    document.querySelector('#email-from').innerHTML = email.sender;
    document.querySelector('#email-to').innerHTML = email.recipients;
    document.querySelector('#email-subject').innerHTML = email.subject;
    document.querySelector('#email-timestamp').innerHTML = email.timestamp;
    document.querySelector('#email-body').innerHTML = `<pre>${email.body}</pre>`;

    // Toggle Archive/Unarchive button
    if (!email.archived) {
      document.querySelector('#archive').innerHTML = "Archive";
      document.querySelector('#archive').onclick = () => archive_email(id, true);
    } else {
      document.querySelector('#archive').innerHTML = "Unarchive";
      document.querySelector('#archive').onclick = () => archive_email(id, false);
    }

    // Hide Archive/Unarchive button for Sent mailbox emails, show for other mailboxes
    if (mailbox === 'sent') {
      document.querySelector('#archive').style.display = 'none';
    } else {
      document.querySelector('#archive').style.display = 'block';
    }
  })
  .catch(error => show_error(error));

  document.querySelector('#reply').onclick = () => reply_email(id);

  // Mark the email as read
  fetch(url, {
    method: 'PUT',
    body: JSON.stringify({
        read: true
    })
  })
}

function send_email() {

  // Get compose url (set dynamically into dataset by back-end)
  const url = document.querySelector('#compose-form').dataset.url;

  // Send mail
  fetch(url, {
    method: 'POST',
    body: JSON.stringify({
      recipients: document.querySelector('#compose-recipients').value,
      subject: document.querySelector('#compose-subject').value,
      body: document.querySelector('#compose-body').value,
    })
  })
  .then(response => response.json())
  .then(result => {
    // Print result
    console.log(result);

    // If sending error, display it. Else, load sent mailbox.
    if (result.error) {
      document.querySelector('#recipients-error').innerHTML = result.error;
      document.querySelector('#compose-recipients').focus();
    } else {
      load_mailbox('sent');
    }
  })
  .catch(error => show_error(error));

  // Prevent default submission
  return false;
}

function archive_email(id, value) {

  console.log('archive', id);

  // Archive/Unarchive email
  fetch(get_email_url(id), {
    method: 'PUT',
    body: JSON.stringify({
        archived: value
    })
  })
  // Once email archived/unarchived, load inbox
  .then(result => {
    load_mailbox('inbox');
  })
  .catch(error => show_error(error));
}

function reply_email(id) {

  console.log('reply', id);

  compose_email();

  // Pre-fill composition fields with original email details
  fetch(get_email_url(id))
  .then(response => response.json())
  .then(email => {
    document.querySelector('#compose-recipients').value = email.sender;
    // Add 'Re:' to original subject, except if it already begins with that
    if (email.subject.slice(0,3).toLowerCase() === 're:') {
      document.querySelector('#compose-subject').value = email.subject;
    } else {
      document.querySelector('#compose-subject').value = `RE: ${email.subject}`;
    }
    document.querySelector('#compose-body').value = `\n\nOn ${email.timestamp} ${email.sender} wrote:\n${email.body}`;
  })
  .catch(error => show_error(error));
}

function show_error(error) {

  console.error(error);
  document.querySelector('#error').innerHTML = error.message;
  window.scrollTo(0, 0);
}

function get_email_url(id) {

  // Get email URL (set dynamically into dataset by back-end)
  const re = /^.*\//;
  const baseUrl = re.exec(document.querySelector('#email-container').dataset.url)[0];
  url = baseUrl + id;
  return url;
}

function update_nav(selectedNavLinkId) {

  // Deactivate all nav-links
  document.querySelectorAll('.nav-link').forEach(item => {
    item.classList.remove('active');
  });

  if (selectedNavLinkId) {
    // Activate selected link
    document.getElementById(selectedNavLinkId).classList.add('active');
  }
}