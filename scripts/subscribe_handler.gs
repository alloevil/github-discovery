// GitHub Discovery Newsletter - Google Apps Script Web App
// 功能：
//   1. doPost: 接收表单订阅，写入 Google Sheet
//   2. doGet: 返回订阅者列表 JSON
//   3. 每次新增订阅后，自动同步到 GitHub 的 subscribers.txt

// ========== 配置 ==========
var SHEET_ID = 'YOUR_SHEET_ID_HERE';  // 替换为你的 Google Sheet ID
var GITHUB_TOKEN = 'YOUR_GITHUB_TOKEN_HERE';  // 替换为 GitHub Personal Access Token
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
    syncToGitHub(email);

    return jsonResponse({status: 'ok'});
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

function syncToGitHub(newEmail) {
  try {
    // 获取当前 subscribers.txt 内容
    var url = 'https://api.github.com/repos/' + GITHUB_REPO + '/contents/subscribers.txt';
    var resp = UrlFetchApp.fetch(url, {
      headers: {'Authorization': 'token ' + GITHUB_TOKEN, 'User-Agent': 'GitHub-Discovery'},
      muteHttpExceptions: true
    });
    var file = JSON.parse(resp.getContentText());
    var sha = file.sha;
    var content = Utilities.newString(Utilities.base64Decode(file.content));

    // 追加新邮箱
    content = content.trim() + '\n' + newEmail + '\n';
    var encoded = Utilities.base64Encode(content);

    // 更新文件
    UrlFetchApp.fetch(url, {
      method: 'put',
      contentType: 'application/json',
      headers: {'Authorization': 'token ' + GITHUB_TOKEN, 'User-Agent': 'GitHub-Discovery'},
      payload: JSON.stringify({
        message: '📧 New subscriber: ' + newEmail,
        content: encoded,
        sha: sha
      }),
      muteHttpExceptions: true
    });
  } catch (err) {
    Logger.log('GitHub sync failed: ' + err.message);
  }
}

function jsonResponse(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
