// For google sheets

// Usage
//  1. Enter sheet name where data is to be written below
//
//  2. Run > setup
//
//  3. Publish > Deploy as web app 
//    - enter Project Version name and click 'Save New Version' 
//    - set security level and enable service (most likely execute as 'me' and access 'anyone, even anonymously) 
//
//  4. Copy the 'Current web app URL' and post this in your form/script action 
//
//  5. Use curl -L -d "action=mistmeter&blur=234&brightness=456" https://script.google.com/macros/s/[SPREADSHEET ID]/exec

var SHEET_NAME = "mistmeter";
var SCRIPT_PROP = PropertiesService.getScriptProperties(); // new property service

// If you don't want to expose either GET or POST methods you can comment out the appropriate function
function doGet(e){
  return handleResponse(e);
}

function doPost(e){
  return handleResponse(e);
}

//----------------------------------------------------------------------------------------

function handleResponse(e) {
  var lock = LockService.getPublicLock();
  lock.waitLock(30000);  // wait 30 seconds before conceding defeat.
  
  try {
    var action = e.parameter.action;
    
    if (action == 'mistmeter') {
      return mistmeter(e);
    } else {
      return geefHint(e);
    }
  } catch(e){
    // if error return this
    return ContentService
          .createTextOutput(JSON.stringify({"result":"error", "error": e}))
          .setMimeType(ContentService.MimeType.JSON);
  } finally { //release lock
    lock.releaseLock();
  }
}

//----------------------------------------------------------------------------------------

function mistmeter(e) {
  var doc = SpreadsheetApp.openById(SCRIPT_PROP.getProperty("key"));
  var sheet = doc.getSheetByName(SHEET_NAME);

  var blur = e.parameter.blur;
  var brightness = e.parameter.brightness;
  var timestamp = e.parameter.timestamp;
  var mist = e.parameter.mist;
  var probability = e.parameter.probability;

  // more efficient to set values as [][] array than individually
  //sheet.getRange(rowId, 1, 1, numColumns).setValues([row]);
  sheet.getRange(1, 2).setValue(blur);
  sheet.getRange(2, 2).setValue(brightness);
  sheet.getRange(3, 2).setValue(timestamp);
  sheet.getRange(4, 2).setValue(mist);
  sheet.getRange(5, 2).setValue(probability);

  // return json success results
  return ContentService
      .createTextOutput(JSON.stringify({
        "result":"success",
        "blur": blur,
        "brightness": brightness,
      }))
      .setMimeType(ContentService.MimeType.JSON);
}

//----------------------------------------------------------------------------------------

function setup() {
    var doc = SpreadsheetApp.getActiveSpreadsheet();
    SCRIPT_PROP.setProperty("key", doc.getId());
}

//------------------------------------------------------------------------------------------

function geefHint(e) {
  Logger.log("Geef een hint");
    return ContentService
    .createTextOutput(JSON.stringify({"result":"fail", "e": e}))
          .setMimeType(ContentService.MimeType.JSON);
}
  