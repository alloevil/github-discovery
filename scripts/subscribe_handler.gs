// GitHub Discovery Newsletter Subscriber Webhook
// Deploy as Google Apps Script Web App
// 1. Go to script.google.com
// 2. Create new project, paste this code
// 3. Deploy → Web App → Execute as: Me → Who has access: Anyone
// 4. Copy the web app URL

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var email = data.email;
    if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      return ContentService.createTextOutput(JSON.stringify({error: 'Invalid email'}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // Open the spreadsheet (create one first, put its ID here)
    var SHEET_ID = 'YOUR_SHEET_ID_HERE';
    var sheet = SpreadsheetApp.openById(SHEET_ID).getActiveSheet();

    // Check if email already exists
    var data = sheet.getDataRange().getValues();
    for (var i = 0; i < data.length; i++) {
      if (data[i][0] === email) {
        return ContentService.createTextOutput(JSON.stringify({status: 'already_subscribed'}))
          .setMimeType(ContentService.MimeType.JSON);
      }
    }

    // Add new subscriber
    sheet.appendRow([email, new Date().toISOString()]);

    return ContentService.createTextOutput(JSON.stringify({status: 'ok'}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({error: err.message}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  // Return subscriber list (for cron to read)
  try {
    var SHEET_ID = 'YOUR_SHEET_ID_HERE';
    var sheet = SpreadsheetApp.openById(SHEET_ID).getActiveSheet();
    var data = sheet.getDataRange().getValues();
    var emails = [];
    for (var i = 0; i < data.length; i++) {
      var email = data[i][0];
      if (email && email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
        emails.push(email);
      }
    }
    return ContentService.createTextOutput(JSON.stringify({subscribers: emails}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({error: err.message}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
