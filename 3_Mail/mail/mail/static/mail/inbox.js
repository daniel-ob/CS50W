document.addEventListener('DOMContentLoaded', function() {

  // Use buttons to toggle between views
  document.querySelector('#inbox').addEventListener('click', () => load_mailbox('inbox'));
  document.querySelector('#sent').addEventListener('click', () => load_mailbox('sent'));
  document.querySelector('#archived').addEventListener('click', () => load_mailbox('archive'));
  document.querySelector('#compose').addEventListener('click', compose_email);

  // By default, load the inbox
  load_mailbox('inbox');
});

function compose_email() {

  // Show compose view and hide other views
  document.querySelector('#emails-view').style.display = 'none';
  document.querySelector('#compose-view').style.display = 'block';

  // Clear out composition fields
  document.querySelector('#compose-recipients').value = '';
  document.querySelector('#compose-subject').value = '';
  document.querySelector('#compose-body').value = '';

  // Clear recipients error
  document.querySelector('#recipients-error').innerHTML = '';
  document.querySelector('#compose-recipients').addEventListener('input', () => {
    document.querySelector('#recipients-error').innerHTML = '';
  });

  // Send email at form submission
  document.querySelector('#compose-form').onsubmit = send_email;
}

function load_mailbox(mailbox) {

  // Show the mailbox and hide other views
  document.querySelector('#emails-view').style.display = 'block';
  document.querySelector('#compose-view').style.display = 'none';

  // Show the mailbox name
  document.querySelector('#inbox-name').innerHTML = `${mailbox.charAt(0).toUpperCase() + mailbox.slice(1)}`;

  // Clear email-container
  document.querySelector('#email-container').innerHTML = '';

  // Get emails
  fetch(`/emails/${mailbox}`)
  .then(response => response.json())
  .then(emails => {
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
      row.addEventListener('click', () => view_email(email.id));
    });
  })
}

function send_email() {

  fetch('/emails', {
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
  });

  // Prevent default submission
  return false;
}
