// GitHub Discovery Newsletter - Google Apps Script Web App
// 功能：
//   1. doPost: 接收表单订阅，写入 Google Sheet，发送确认邮件
//   2. doGet: 返回订阅者列表 JSON
//   3. 每次新增订阅后，自动同步到 GitHub 的 subscribers.txt

// ========== 配置 ==========
var SHEET_ID = '1YoiRZ73frrij_98gcUtEjmw29yuXGFhoHUHzkwO-Ubo';
var GITHUB_TOKEN = 'YOUR_G…HERE';
var GITHUB_REPO = 'alloevil/github-discovery';
// ===========================

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var email = data.email;
    if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      return jsonResponse({error: 'Invalid email'});
    }

    var sheet = SpreadsheetApp.openById(SHEET_ID).getActiveSheet();
    var rows = sheet.getDataRange().getValues();

    // 检查是否已订阅
    for (var i = 0; i < rows.length; i++) {
      if (rows[i][0] === email) {
        return jsonResponse({status: 'already_subscribed'});
      }
    }

    // 写入 Sheet
    sheet.appendRow([email, new Date().toISOString()]);

    // 同步到 GitHub
    var syncResult = syncToGitHub(email);

    // 发送确认邮件
    sendConfirmEmail(email);

    return jsonResponse({status: 'ok', sync: syncResult});
  } catch (err) {
    return jsonResponse({error: err.message});
  }
}

function doGet(e) {
  try {
    var sheet = SpreadsheetApp.openById(SHEET_ID).getActiveSheet();
    var rows = sheet.getDataRange().getValues();
    var emails = [];
    for (var i = 0; i < rows.length; i++) {
      if (rows[i][0] && rows[i][0].match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
        emails.push(rows[i][0]);
      }
    }
    return jsonResponse({subscribers: emails});
  } catch (err) {
    return jsonResponse({error: err.message});
  }
}

function sendConfirmEmail(email) {
  try {
    MailApp.sendEmail({
      to: email,
      subject: '✅ GitHub Discovery Newsletter 订阅确认',
      htmlBody: '<div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px;">' +
        '<h2 style="color:#1a73e8;">🎉 订阅成功！</h2>' +
        '<p>感谢你订阅 <strong>GitHub Discovery Newsletter</strong>！</p>' +
        '<p>你将收到精选的 GitHub 优质项目推荐，帮助你发现更多好项目。</p>' +
        '<hr style="border:none;border-top:1px solid #eee;margin:20px 0;">' +
        '<p style="color:#666;font-size:12px;">如需退订，请回复邮件说明即可。</p>' +
        '</div>',
      noReply: true
    });
    Logger.log('✅ Confirmation email sent to: ' + email);
  } catch (err) {
    Logger.log('❌ Email send failed: ' + err.message);
  }
}

function syncToGitHub(newEmail) {
  try {
    var url = 'https://api.github.com/repos/' + GITHUB_REPO + '/contents/subscribers.txt';
    var tokenHeader = 'Bearer ' + GITHUB_TOKEN;
    var resp = UrlFetchApp.fetch(url, {
      headers: {'Authorization': tokenHeader, 'User-Agent': 'GitHub-Discovery'},
      muteHttpExceptions: true
    });

    var result = {getStatus: resp.getResponseCode()};

    if (resp.getResponseCode() !== 200) {
      result.getError = resp.getContentText().substring(0, 300);
      return result;
    }

    var file = JSON.parse(resp.getContentText());
    var sha = file.sha;
    var content = Utilities.newBlob(Utilities.base64Decode(file.content)).getDataAsString();
    content = content.trim() + '\n' + newEmail + '\n';
    var encoded = Utilities.base64Encode(content);

    var putResp = UrlFetchApp.fetch(url, {
      method: 'put',
      contentType: 'application/json',
      headers: {'Authorization': tokenHeader, 'User-Agent': 'GitHub-Discovery'},
      payload: JSON.stringify({
        message: '📧 New subscriber: ' + newEmail,
        content: encoded,
        sha: sha
      }),
      muteHttpExceptions: true
    });

    result.putStatus = putResp.getResponseCode();
    result.putBody = putResp.getContentText().substring(0, 300);
    return result;

  } catch (err) {
    return {error: err.message};
  }
}

function jsonResponse(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
