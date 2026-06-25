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
      subject: '✅ GitHub Discovery Newsletter — Subscription Confirmed',
      htmlBody: '<!DOCTYPE html>' +
        '<html>' +
        '<head>' +
        '<meta charset="utf-8">' +
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">' +
        '<meta name="color-scheme" content="light dark">' +
        '<meta name="supported-color-schemes" content="light dark">' +
        '</head>' +
        '<body style="margin:0;padding:0;background:#f8f9fa;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,Helvetica,Arial,sans-serif;">' +
        '<div style="max-width:600px;margin:0 auto;padding:40px 20px;">' +
        '<!-- Header -->' +
        '<div style="text-align:center;margin-bottom:32px;">' +
        '<div style="font-size:32px;margin-bottom:8px;">🔥</div>' +
        '<h1 style="margin:0;font-size:24px;font-weight:700;color:#1a1a2e;">GitHub Discovery</h1>' +
        '<p style="margin:8px 0 0;font-size:14px;color:#6b7280;">Discover trending repos before they go mainstream</p>' +
        '</div>' +
        '<!-- Content -->' +
        '<div style="background:#ffffff;border-radius:12px;padding:32px;border:1px solid #e5e7eb;">' +
        '<h2 style="margin:0 0 16px;font-size:20px;font-weight:600;color:#1a1a2e;">Welcome aboard! 🎉</h2>' +
        '<p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#374151;">Thank you for subscribing to <strong>GitHub Discovery Newsletter</strong>. You\'ll receive daily curated GitHub repositories with smart scoring and anti-spam filtering.</p>' +
        '<p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#374151;">Every day, we analyze 5 data sources, score 100+ repos, and deliver the top picks to your inbox.</p>' +
        '<div style="text-align:center;">' +
        '<a href="https://alloevil.github.io/github-discovery/" style="display:inline-block;padding:12px 24px;background:#1a1a2e;color:#ffffff;text-decoration:none;border-radius:8px;font-size:14px;font-weight:600;">View Today\'s Picks →</a>' +
        '</div>' +
        '</div>' +
        '<!-- Footer -->' +
        '<div style="text-align:center;margin-top:24px;">' +
        '<p style="margin:0;font-size:12px;color:#9ca3af;">To unsubscribe, reply to this email with "unsubscribe".</p>' +
        '<p style="margin:8px 0 0;font-size:12px;color:#9ca3af;">' +
        '<a href="https://github.com/alloevil/github-discovery" style="color:#6b7280;text-decoration:none;">GitHub</a> · ' +
        '<a href="https://alloevil.github.io/github-discovery/" style="color:#6b7280;text-decoration:none;">Website</a> · ' +
        '<a href="https://alloevil.github.io/github-discovery/feed.xml" style="color:#6b7280;text-decoration:none;">RSS</a>' +
        '</p>' +
        '</div>' +
        '</div>' +
        '</body>' +
        '</html>',
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
