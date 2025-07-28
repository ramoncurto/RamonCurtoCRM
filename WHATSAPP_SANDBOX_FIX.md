# 🔧 WhatsApp Sandbox Error Fix Guide

## 🚨 **Error: "Channel Sandbox can only send messages to phone numbers that have joined the Sandbox"**

### **Problem Explanation**
You're using WhatsApp Business API in **sandbox mode**, which restricts message sending to only phone numbers that have explicitly joined your sandbox environment.

---

## 🎯 **Solution Options**

### **Option 1: Exit Sandbox Mode (Recommended)**

#### Step 1: Submit App for Review
1. **Go to:** https://developers.facebook.com/
2. **Navigate to your WhatsApp Business app**
3. **Go to "App Review" → "Submit for Review"**
4. **Provide required business documentation:**
   - Business verification documents
   - Use case description
   - Privacy policy
   - Terms of service

#### Step 2: Wait for Approval
- **Review time:** 1-3 business days
- **Status updates:** Check dashboard regularly
- **Email notifications:** You'll receive updates via email

#### Step 3: Configure Production
Once approved:
- Your app exits sandbox mode
- You can send messages to any verified phone number
- No restrictions on recipient phone numbers

---

### **Option 2: Add Phone Numbers to Sandbox (Temporary)**

#### Step 1: Access Sandbox Settings
1. **Go to:** https://developers.facebook.com/
2. **Navigate to your WhatsApp Business app**
3. **Go to "WhatsApp" → "Getting Started"**
4. **Find "Sandbox" section**

#### Step 2: Add Test Phone Numbers
1. **Add the athlete's phone number:** `+34 679795648`
2. **Send verification code** to the number
3. **Enter the verification code** in the dashboard
4. **Confirm the number** is added to sandbox

#### Step 3: Test with Added Numbers
- Only these added numbers can receive messages
- Add all athlete phone numbers you need to test with
- This is temporary until you exit sandbox mode

---

### **Option 3: Switch to Twilio WhatsApp (Alternative)**

Twilio's WhatsApp API doesn't have sandbox restrictions:

#### Step 1: Create Twilio Account
1. **Go to:** https://www.twilio.com/
2. **Create free account**
3. **Verify your phone number** for WhatsApp

#### Step 2: Get Twilio Credentials
1. **Account SID:** Dashboard → "Account Info"
2. **Auth Token:** Dashboard → "Account Info"  
3. **WhatsApp Number:** Your verified number

#### Step 3: Update Environment Variables
```bash
# Remove Meta credentials
unset WHATSAPP_PHONE_ID
unset WHATSAPP_ACCESS_TOKEN

# Add Twilio credentials
export TWILIO_ACCOUNT_SID="your_account_sid"
export TWILIO_AUTH_TOKEN="your_auth_token"
export TWILIO_WHATSAPP_NUMBER="+1234567890"
```

#### Step 4: Update .env File
```env
# Remove Meta WhatsApp
# WHATSAPP_PHONE_ID=xxx
# WHATSAPP_ACCESS_TOKEN=xxx

# Add Twilio WhatsApp
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=+1234567890
```

---

## 🧪 **Testing the Fix**

### **Test Current Configuration**
```bash
# Check current WhatsApp setup
curl http://localhost:8000/test/whatsapp-config
```

### **Test Message Sending**
1. **Go to:** http://localhost:8000/communication-hub
2. **Select an athlete** with phone number
3. **Send test message** via WhatsApp
4. **Check response** for success/error

### **Expected Results**

#### ✅ **Success (Production Mode)**
```json
{
    "status": "sent",
    "message": "Message sent via WhatsApp to [Athlete Name]",
    "platform": "whatsapp"
}
```

#### ✅ **Success (Sandbox with Added Numbers)**
```json
{
    "status": "sent", 
    "message": "Message sent via WhatsApp to [Athlete Name]",
    "platform": "whatsapp"
}
```

#### ❌ **Error (Sandbox with Unverified Numbers)**
```json
{
    "status": "error",
    "message": "WhatsApp sending failed: Channel Sandbox can only send messages to phone numbers that have joined the Sandbox"
}
```

---

## 📋 **Quick Fix Steps**

### **Immediate Solution (Add to Sandbox)**
1. **Add phone number `+34 679795648` to your WhatsApp sandbox**
2. **Wait for verification code**
3. **Enter code in Meta dashboard**
4. **Test message sending again**

### **Long-term Solution (Exit Sandbox)**
1. **Submit app for review** in Meta for Developers
2. **Wait for approval** (1-3 days)
3. **Configure production webhook**
4. **Test with any phone number**

---

## 🔍 **Troubleshooting**

### **Error: "Phone number not found in sandbox"**
- **Solution:** Add the phone number to your sandbox
- **Process:** Send verification code → Enter code → Confirm

### **Error: "App not approved for production"**
- **Solution:** Submit app for review
- **Required:** Business documentation and use case

### **Error: "Invalid access token"**
- **Solution:** Regenerate access token in Meta dashboard
- **Location:** WhatsApp → API Setup → Access token

### **Error: "Phone number not verified"**
- **Solution:** Verify your business phone number
- **Process:** SMS verification → Enter code → Confirm

---

## 📞 **Support Resources**

- **Meta for Developers:** https://developers.facebook.com/
- **WhatsApp Business API Docs:** https://developers.facebook.com/docs/whatsapp
- **Twilio WhatsApp:** https://www.twilio.com/whatsapp
- **App Review Guidelines:** https://developers.facebook.com/docs/app-review

---

## 🎯 **Recommended Action**

**For immediate testing:** Add the athlete's phone number to your sandbox
**For production use:** Submit your app for review to exit sandbox mode

The sandbox restriction is a security feature to prevent spam. Once you exit sandbox mode, you'll be able to send messages to any verified phone number. 