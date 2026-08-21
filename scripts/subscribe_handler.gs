// GitHub Discovery Newsletter - Google Apps Script Web App
// 功能：
//   1. doPost: 接收表单订阅（双重确认：先登记 pending，发确认邮件，点击后生效）
//   2. doGet ?action=confirm:     确认订阅 → 标记 active + 同步 GitHub + 欢迎邮件
//   3. doGet ?action=unsubscribe: 一键退订 → 移除订阅者 + 同步 GitHub + 确认页
//      （doPost 同样处理 action=unsubscribe —— RFC 8058 one-click 退订头
//        会向 List-Unsubscribe URL 发 POST）
//   4. doGet（无 action）: 返回 active 订阅者列表 JSON

// ========== 配置 ==========
// 注意：不要把真实 token/secret 写进这里并提交到 git。
// 在 Apps Script 控制台用 PropertiesService 存储敏感值：
//   项目设置 → 脚本属性 添加 GITHUB_TOKEN 和 UNSUBSCRIBE_SECRET。
// UNSUBSCRIBE_SECRET 必须与 GitHub Actions 的 UNSUBSCRIBE_SECRET secret
// 一致（scripts/main.py 用它给 digest 里的退订链接签名）。
var SHEET_ID = '1YoiRZ73frrij_98gcUtEjmw29yuXGFhoHUHzkwO-Ubo';
var GITHUB_TOKEN = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN') || 'YOUR_GITHUB_TOKEN_HERE';
var UNSUBSCRIBE_SECRET = PropertiesService.getScriptProperties().getProperty('UNSUBSCRIBE_SECRET') || '';
var GITHUB_REPO = 'alloevil/github-discovery';
var STATUS_PENDING = 'pending';
var STATUS_ACTIVE = 'active';
// ===========================

function doPost(e) {
  try {
    // RFC 8058 one-click 退订：邮件客户端向 List-Unsubscribe URL 发 POST
    if (e.parameter && e.parameter.action === 'unsubscribe') {
      return handleUnsubscribe(e.parameter.email, e.parameter.token);
    }

    var data = JSON.parse(e.postData.contents);
    var email = (data.email || '').trim().toLowerCase();
    if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      return jsonResponse({error: 'Invalid email'});
    }

    var sheet = SpreadsheetApp.openById(SHEET_ID).getActiveSheet();
    var rows = sheet.getDataRange().getValues();

    // 已在表中：active → 已订阅；pending → 重发确认邮件
    for (var i = 0; i < rows.length; i++) {
      if ((rows[i][0] || '').toString().toLowerCase() === email) {
        var status = (rows[i][2] || STATUS_ACTIVE).toString();  // 旧行无状态列 = active
        if (status === STATUS_PENDING) {
          sendConfirmOptInEmail(email);
          return jsonResponse({status: 'confirmation_resent'});
        }
        return jsonResponse({status: 'already_subscribed'});
      }
    }

    // 双重确认（#10）：先登记 pending，确认链接点击后才生效 ——
    // 防止任何人替别人的邮箱订阅。
    sheet.appendRow([email, new Date().toISOString(), STATUS_PENDING]);
    sendConfirmOptInEmail(email);
    return jsonResponse({status: 'pending_confirmation'});
  } catch (err) {
    return jsonResponse({error: err.message});
  }
}

function doGet(e) {
  try {
    var action = e && e.parameter ? e.parameter.action : '';
    if (action === 'confirm') {
      return handleConfirm(e.parameter.email, e.parameter.token);
    }
    if (action === 'unsubscribe') {
      return handleUnsubscribe(e.parameter.email, e.parameter.token);
    }

    // 默认：active 订阅者列表（pending 不算订阅者）
    var sheet = SpreadsheetApp.openById(SHEET_ID).getActiveSheet();
    var rows = sheet.getDataRange().getValues();
    var emails = [];
    for (var i = 0; i < rows.length; i++) {
      var status = (rows[i][2] || STATUS_ACTIVE).toString();
      if (rows[i][0] && rows[i][0].match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/) && status === STATUS_ACTIVE) {
        emails.push(rows[i][0]);
      }
    }
    return jsonResponse({subscribers: emails});
  } catch (err) {
    return jsonResponse({error: err.message});
  }
}

// ========== 订阅确认（double opt-in） ==========

function handleConfirm(email, token) {
  email = (email || '').trim().toLowerCase();
  if (!verifyToken(email, token)) {
    return htmlPage('Invalid link', 'This confirmation link is invalid or has expired.');
  }
  var sheet = SpreadsheetApp.openById(SHEET_ID).getActiveSheet();
  var rows = sheet.getDataRange().getValues();
  for (var i = 0; i < rows.length; i++) {
    if ((rows[i][0] || '').toString().toLowerCase() === email) {
      var status = (rows[i][2] || STATUS_ACTIVE).toString();
      if (status === STATUS_ACTIVE) {
        return htmlPage('Already confirmed', 'Your subscription is already active. See you in the next digest!');
      }
      sheet.getRange(i + 1, 3).setValue(STATUS_ACTIVE);
      syncToGitHub(email);
      sendWelcomeEmail(email);
      return htmlPage('Subscription confirmed 🎉',
        'You\'re in! The daily GitHub Discovery digest will land in your inbox from tomorrow.');
    }
  }
  return htmlPage('Not found', 'This address is not registered. Subscribe again from the website.');
}

// ========== 一键退订 ==========

function handleUnsubscribe(email, token) {
  email = (email || '').trim().toLowerCase();
  if (!verifyToken(email, token)) {
    return htmlPage('Invalid link', 'This unsubscribe link is invalid. Please use the link from a recent digest email.');
  }
  var sheet = SpreadsheetApp.openById(SHEET_ID).getActiveSheet();
  var rows = sheet.getDataRange().getValues();
  var found = false;
  // 从下往上删，避免删除后行号位移
  for (var i = rows.length - 1; i >= 0; i--) {
    if ((rows[i][0] || '').toString().toLowerCase() === email) {
      sheet.deleteRow(i + 1);
      found = true;
    }
  }
  if (found) {
    removeFromGitHub(email);
  }
  // 未找到也返回成功页：退订必须幂等，且不应泄露某地址是否在列表中
  return htmlPage('Unsubscribed ✅',
    'You have been removed from the GitHub Discovery digest. Sorry to see you go — you can re-subscribe on the website any time.');
}

// ========== Token ==========

// token = hex(HMAC-SHA256(UNSUBSCRIBE_SECRET, lowercase(email)))
// 与 scripts/main.py 的 unsubscribe_token() 完全一致。
function computeToken(email) {
  var sig = Utilities.computeHmacSha256Signature(email, UNSUBSCRIBE_SECRET);
  return sig.map(function (b) {
    var v = (b < 0 ? b + 256 : b).toString(16);
    return v.length === 1 ? '0' + v : v;
  }).join('');
}

function verifyToken(email, token) {
  if (!UNSUBSCRIBE_SECRET || !email || !token) return false;
  return computeToken(email) === token.toLowerCase();
}

function selfUrl() {
  return ScriptApp.getService().getUrl();
}

// ========== 邮件 ==========

function sendConfirmOptInEmail(email) {
  try {
    var confirmUrl = selfUrl() + '?action=confirm&email=' + encodeURIComponent(email) +
      '&token=' + computeToken(email);
    MailApp.sendEmail({
      to: email,
      subject: '🔥 GitHub Discovery — Confirm your subscription',
      htmlBody: '<!DOCTYPE html>' +
        '<html><head><meta charset="utf-8"></head>' +
        '<body style="margin:0;padding:0;background:#f8f9fa;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,Helvetica,Arial,sans-serif;">' +
        '<div style="max-width:600px;margin:0 auto;padding:40px 20px;">' +
        '<div style="text-align:center;margin-bottom:32px;">' +
        '<div style="font-size:32px;margin-bottom:8px;">🔥</div>' +
        '<h1 style="margin:0;font-size:24px;font-weight:700;color:#1a1a2e;">GitHub Discovery</h1>' +
        '</div>' +
        '<div style="background:#ffffff;border-radius:12px;padding:32px;border:1px solid #e5e7eb;">' +
        '<h2 style="margin:0 0 16px;font-size:20px;font-weight:600;color:#1a1a2e;">One more step</h2>' +
        '<p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#374151;">Someone (hopefully you) asked to receive the daily GitHub Discovery digest at <strong>' + email + '</strong>. Click below to confirm — if this wasn\'t you, just ignore this email and nothing will be sent.</p>' +
        '<div style="text-align:center;">' +
        '<a href="' + confirmUrl + '" style="display:inline-block;padding:12px 24px;background:#1a1a2e;color:#ffffff;text-decoration:none;border-radius:8px;font-size:14px;font-weight:600;">Confirm Subscription →</a>' +
        '</div>' +
        '</div>' +
        '</div></body></html>',
      noReply: true
    });
    Logger.log('✅ Opt-in confirmation sent to: ' + email);
  } catch (err) {
    Logger.log('❌ Opt-in email failed: ' + err.message);
  }
}

function sendWelcomeEmail(email) {
  try {
    var unsubUrl = selfUrl() + '?action=unsubscribe&email=' + encodeURIComponent(email) +
      '&token=' + computeToken(email);
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
        '<p style="margin:0;font-size:12px;color:#9ca3af;"><a href="' + unsubUrl + '" style="color:#6b7280;">Unsubscribe</a> with one click any time.</p>' +
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
    Logger.log('✅ Welcome email sent to: ' + email);
  } catch (err) {
    Logger.log('❌ Email send failed: ' + err.message);
  }
}

// ========== GitHub subscribers.txt 同步 ==========

function syncToGitHub(newEmail) {
  return updateSubscribersFile(function (content) {
    var lines = content.split('\n').map(function (l) { return l.trim(); }).filter(Boolean);
    if (lines.indexOf(newEmail) !== -1) return null;  // 已存在，无需提交
    return content.trim() + '\n' + newEmail + '\n';
  }, '📧 New subscriber: ' + newEmail);
}

function removeFromGitHub(email) {
  return updateSubscribersFile(function (content) {
    var lines = content.split('\n');
    var kept = lines.filter(function (l) { return l.trim().toLowerCase() !== email; });
    if (kept.length === lines.length) return null;  // 不在文件中，无需提交
    return kept.join('\n');
  }, '📭 Unsubscribed: ' + email);
}

function updateSubscribersFile(transform, message) {
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
    var content = Utilities.newBlob(Utilities.base64Decode(file.content)).getDataAsString();
    var updated = transform(content);
    if (updated === null) {
      result.skipped = true;
      return result;
    }
    var encoded = Utilities.base64Encode(updated);

    var putResp = UrlFetchApp.fetch(url, {
      method: 'put',
      contentType: 'application/json',
      headers: {'Authorization': tokenHeader, 'User-Agent': 'GitHub-Discovery'},
      payload: JSON.stringify({
        message: message,
        content: encoded,
        sha: file.sha
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

// ========== 响应工具 ==========

function jsonResponse(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function htmlPage(title, message) {
  return HtmlService.createHtmlOutput(
    '<!DOCTYPE html><html><head><meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<title>' + title + ' — GitHub Discovery</title></head>' +
    '<body style="margin:0;background:#f8f9fa;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,Helvetica,Arial,sans-serif;">' +
    '<div style="max-width:480px;margin:80px auto;padding:40px 32px;background:#fff;border:1px solid #e5e7eb;border-radius:12px;text-align:center;">' +
    '<div style="font-size:32px;margin-bottom:12px;">🔥</div>' +
    '<h1 style="margin:0 0 12px;font-size:22px;color:#1a1a2e;">' + title + '</h1>' +
    '<p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#374151;">' + message + '</p>' +
    '<a href="https://alloevil.github.io/github-discovery/" style="color:#6b7280;font-size:13px;">← GitHub Discovery</a>' +
    '</div></body></html>');
}
