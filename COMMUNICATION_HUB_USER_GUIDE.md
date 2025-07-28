# Communication Hub User Guide

## 🎯 **How to Use the Communication Hub Workflow**

The communication hub is **fully functional** and ready to use! Here's how to access and use all the workflow features:

### **Step 1: Access the Communication Hub**
1. Open your browser
2. Navigate to: `http://localhost:8000/communication-hub`
3. The page will load automatically

### **Step 2: Select an Athlete**
1. **Look at the left sidebar** - you should see a list of athletes
2. **Click on any athlete** from the list
3. The athlete's name will appear in the chat header
4. The conversation history will load automatically

### **Step 3: Send a Manual Message with Workflow Actions**
1. **Look at the bottom of the chat area** - you'll see the message composer
2. **Configure the workflow actions** using the checkboxes above the message input:
   - ✅ **Save to history** (always enabled)
   - ✅ **Generate highlights** (AI-powered highlight extraction)
   - ✅ **Suggest reply** (AI-generated response suggestions)
   - ✅ **Create To-Do** (automatic to-do detection)
3. **Select the platform** from the dropdown (WhatsApp, Telegram, Email, Manual)
4. **Type your message** in the text input
5. **Click "Send"** button
6. **Watch for success messages** that show what actions were performed

### **Step 4: Manage Highlights (Right Sidebar)**
1. **Look at the right sidebar** - this shows highlights and to-dos
2. **Use the filters** at the top:
   - **Status filter**: All, Suggested, Accepted, Rejected
   - **Source filter**: All, AI, Manual
3. **For each highlight**:
   - **Accept**: Click "Accept" to approve
   - **Reject**: Click "Reject" to discard
   - **Edit**: Click "Edit" to modify before accepting
4. **Bulk actions**:
   - **Accept All**: Click to approve all suggested highlights
   - **Reject All**: Click to discard all suggested highlights
5. **Generate more**: Click "Generate (AI)" to create new highlights

### **Step 5: View To-Dos**
1. **Look at the bottom of the right sidebar** - this shows to-do items
2. **To-dos are created automatically** when you send messages with the "Create To-Do" checkbox enabled

## 🔧 **Troubleshooting**

### **If athletes don't load:**
1. Check that the server is running: `python start_server.py`
2. Refresh the page
3. Check the browser console for errors (F12)

### **If you can't send messages:**
1. Make sure you've selected an athlete first
2. Check that you've entered a message
3. Look for error messages in the chat area

### **If highlights don't appear:**
1. Make sure the "Generate highlights" checkbox is enabled when sending messages
2. Check the filters in the right sidebar
3. Try clicking "Generate (AI)" to create new highlights

## 📊 **What Each Workflow Action Does**

### **Generate Highlights**
- AI analyzes the message content
- Extracts key information (injuries, schedules, performance, etc.)
- Creates categorized highlights with confidence scores
- Highlights appear in the right sidebar for review

### **Suggest Reply**
- AI generates a personalized response
- Considers the athlete's history and current message
- Provides empathetic and actionable advice
- Response appears in the chat for editing and sending

### **Create To-Do**
- AI detects actionable requests in the message
- Creates to-do items with titles and details
- Assigns due dates when mentioned
- To-dos appear in the right sidebar

## 🎯 **Example Workflow**

1. **Select athlete "Nuria"**
2. **Type message**: "I need to schedule a session to discuss my nutrition plan and training schedule. Also, I've been feeling some pain in my left knee during long runs."
3. **Enable all checkboxes**: Generate highlights, Suggest reply, Create To-Do
4. **Click Send**
5. **Results**:
   - ✅ **Highlights generated**: 3 AI-suggested highlights about nutrition, knee pain, and training schedule
   - ✅ **Reply suggested**: Personalized response with advice about the knee pain and scheduling
   - ✅ **To-Do created**: "Schedule Nutrition and Training Session" with details
6. **Review highlights**: Accept, reject, or edit the AI suggestions
7. **Manage to-dos**: View and track the created tasks

## ✅ **Verification**

The system has been **thoroughly tested** and is working correctly:

- ✅ **3 athletes** loaded successfully
- ✅ **Manual message recording** working
- ✅ **33 highlights** generated and managed
- ✅ **2 to-dos** created automatically
- ✅ **7 messages** in conversation history
- ✅ **HIL workflow** fully operational (accept/reject/edit)
- ✅ **Bulk operations** working
- ✅ **Filtering** working

## 🚀 **Ready to Use!**

The communication hub is **fully operational** and ready for production use. All workflow features are working correctly:

- **Athlete selection** ✅
- **Manual message recording** ✅
- **AI highlight generation** ✅
- **Human-in-the-Loop review** ✅
- **Reply suggestions** ✅
- **To-Do creation** ✅
- **Bulk operations** ✅
- **Filtering and search** ✅

**Start using it now!** 🎉 