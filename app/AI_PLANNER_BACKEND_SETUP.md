# AI Planner Backend Setup Guide

This guide will help you set up the complete backend infrastructure for your Jharkhand Tourism AI Planner using Supabase.

## 🚀 Quick Start

### 1. Set Up Supabase Project

1. **Create Supabase Account**
   - Go to [supabase.com](https://supabase.com)
   - Sign up for a free account
   - Create a new project

2. **Get Your Credentials**
   - In your Supabase dashboard, go to **Settings** → **API**
   - Copy your **Project URL** and **anon public key**

3. **Configure Your Project**
   - Open `supabase-config.js`
   - Replace the placeholder values:
   ```javascript
   const SUPABASE_URL = 'your_actual_project_url_here'
   const SUPABASE_ANON_KEY = 'your_actual_anon_key_here'
   ```

### 2. Set Up Database

1. **Run Database Schema**
   - In your Supabase dashboard, go to **SQL Editor**
   - Copy and paste the contents of `database-schema.sql`
   - Click **Run** to create all tables and policies

2. **Verify Tables Created**
   - Go to **Table Editor** in your Supabase dashboard
   - You should see these tables:
     - `user_profiles`
     - `itineraries`
     - `itinerary_days`
     - `saved_destinations`
     - `user_feedback`
     - `ai_interactions`
     - `travel_insights`

### 3. Configure Authentication

1. **Set Up Site URL**
   - Go to **Authentication** → **Settings**
   - Add your domain to **Site URL** (e.g., `https://yourdomain.com` or `http://localhost:3000`)

2. **Configure Redirect URLs**
   - Add these URLs to **Redirect URLs**:
     - `https://yourdomain.com/login.html`
     - `https://yourdomain.com/signup.html`
     - `https://yourdomain.com/reset-password.html`
     - `https://yourdomain.com/main page.html`

3. **Set Up Email Templates** (Optional)
   - Go to **Authentication** → **Email Templates**
   - Customize the email templates for your brand

## 📁 File Structure

```
your-project/
├── main page.html              # Main page with AI planner integration
├── login.html                  # Login page with Supabase auth
├── signup.html                 # Registration page
├── reset-password.html         # Password reset page
├── supabase-config.js          # Supabase client configuration
├── auth-service.js             # Authentication service
├── planner-service.js          # Core planner CRUD operations
├── preferences-service.js      # User preferences management
├── itinerary-manager.js        # AI itinerary generation
├── analytics-service.js        # Analytics and insights
├── database-schema.sql         # Database schema
└── AI_PLANNER_BACKEND_SETUP.md # This setup guide
```

## 🔧 Features Included

### ✅ Authentication System
- User registration with email verification
- Secure login/logout
- Password reset functionality
- Session management
- Row-level security (RLS)

### ✅ AI Planner Backend
- **Itinerary Generation**: AI-powered trip planning
- **Data Storage**: Save and manage itineraries
- **User Preferences**: Personalized planning based on user data
- **Destination Management**: Save and track favorite places
- **Analytics**: Travel insights and recommendations

### ✅ Data Management
- **Itineraries**: Complete trip plans with day-by-day details
- **User Profiles**: Personal information and preferences
- **Saved Destinations**: Favorite places and wishlist
- **AI Interactions**: Track user queries and responses
- **Feedback System**: User ratings and suggestions
- **Travel Insights**: Analytics and recommendations

### ✅ Advanced Features
- **Offline Mode**: Works without authentication
- **Real-time Updates**: Live data synchronization
- **Data Export/Import**: Backup and restore preferences
- **Sharing**: Public itinerary sharing
- **Duplication**: Copy existing itineraries
- **Search & Filter**: Find itineraries by criteria

## 🎯 How It Works

### 1. User Authentication
```javascript
// Check if user is logged in
const { data: { user } } = await supabase.auth.getUser()

if (user) {
    // User is authenticated - use backend features
    const result = await ItineraryManager.generateItinerary(formData)
} else {
    // User not authenticated - use offline mode
    generateItinerary() // Original function
}
```

### 2. AI Itinerary Generation
```javascript
// Generate personalized itinerary
const formData = {
    duration: 'weekend',
    budget: 'mid',
    travelers: 2,
    interests: { mountains: true, waterfalls: true },
    needs: { wheelchair: false, kidFriendly: true }
}

const result = await ItineraryManager.generateItinerary(formData)
```

### 3. Data Storage
```javascript
// Save itinerary to database
const itinerary = await PlannerService.createItinerary({
    title: '3-Day Mountain Adventure',
    duration_days: 3,
    budget_range: 'mid',
    destinations: ['Netarhat', 'Hundru Falls'],
    // ... more data
})
```

### 4. User Preferences
```javascript
// Get user preferences
const prefs = await PreferencesService.getPreferences()

// Update preferences
await PreferencesService.updateTravelPreferences({
    preferred_duration: 'weekend',
    budget_range: 'mid',
    interests: { mountains: true }
})
```

## 🔒 Security Features

### Row Level Security (RLS)
- Users can only access their own data
- Public itineraries are viewable by all users
- Secure API endpoints with authentication

### Data Validation
- Input validation on all forms
- SQL injection protection
- XSS prevention

### Privacy Controls
- User data is private by default
- Optional public sharing
- Data retention policies

## 📊 Analytics & Insights

### User Analytics
- Travel patterns and preferences
- Budget analysis and optimization
- Seasonal travel trends
- AI usage statistics

### Recommendations
- Personalized destination suggestions
- Activity recommendations
- Budget optimization tips
- Seasonal travel advice

## 🚀 Deployment

### 1. Static Hosting (Recommended)
- **Netlify**: Connect your GitHub repo
- **Vercel**: Deploy with zero configuration
- **GitHub Pages**: Free hosting for static sites

### 2. Environment Variables
Set these in your hosting platform:
```
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
```

### 3. Domain Configuration
Update your Supabase settings with your production domain:
- Site URL: `https://yourdomain.com`
- Redirect URLs: `https://yourdomain.com/*`

## 🧪 Testing

### 1. Test Authentication
1. Open your website
2. Click "Login" and create an account
3. Verify email (check your inbox)
4. Login and test the AI planner

### 2. Test AI Planner
1. Open the AI Planner modal
2. Fill in your preferences
3. Generate an itinerary
4. Verify it's saved to your account

### 3. Test Data Persistence
1. Create multiple itineraries
2. Log out and log back in
3. Verify your data is still there

## 🐛 Troubleshooting

### Common Issues

**"Invalid API key" error**
- Double-check your SUPABASE_URL and SUPABASE_ANON_KEY
- Ensure no extra spaces or characters

**"User not authenticated" error**
- Check if user is logged in
- Verify authentication is working

**Database errors**
- Ensure you've run the database schema
- Check RLS policies are enabled

**Email verification not working**
- Check your email settings in Supabase
- Verify redirect URLs are correct

### Getting Help

1. **Check Browser Console**: Look for error messages
2. **Supabase Dashboard**: Check logs in the dashboard
3. **Documentation**: [Supabase Docs](https://supabase.com/docs)
4. **Community**: [Supabase Discord](https://discord.supabase.com)

## 📈 Performance Optimization

### Database Optimization
- Indexes are already created for optimal performance
- RLS policies ensure efficient queries
- Connection pooling is handled by Supabase

### Frontend Optimization
- Lazy loading of modules
- Efficient state management
- Minimal API calls

### Caching
- User preferences are cached locally
- Itineraries are cached for offline access
- Real-time updates when online

## 🔄 Updates & Maintenance

### Regular Maintenance
- Monitor Supabase usage and limits
- Update dependencies regularly
- Backup user data periodically

### Scaling
- Supabase handles automatic scaling
- Upgrade plan as user base grows
- Monitor performance metrics

## 📝 API Reference

### PlannerService
```javascript
// Create itinerary
await PlannerService.createItinerary(data)

// Get user itineraries
await PlannerService.getItineraries()

// Update itinerary
await PlannerService.updateItinerary(id, data)

// Delete itinerary
await PlannerService.deleteItinerary(id)
```

### PreferencesService
```javascript
// Get preferences
await PreferencesService.getPreferences()

// Update preferences
await PreferencesService.updatePreferences(data)

// Get specific category
await PreferencesService.getTravelPreferences()
```

### ItineraryManager
```javascript
// Generate AI itinerary
await ItineraryManager.generateItinerary(formData)

// Duplicate itinerary
await ItineraryManager.duplicateItinerary(id)
```

### AnalyticsService
```javascript
// Get user analytics
await AnalyticsService.getUserAnalytics()

// Get travel insights
await AnalyticsService.getTravelInsights()
```

## 🎉 You're All Set!

Your AI Planner backend is now ready! Users can:

1. **Register and Login** securely
2. **Generate AI-powered itineraries** based on their preferences
3. **Save and manage** their travel plans
4. **Track their travel history** and get insights
5. **Share itineraries** with others
6. **Get personalized recommendations**

The system works both online (with full features) and offline (basic functionality), ensuring a great user experience regardless of connectivity.

## 🆘 Support

If you need help or have questions:

1. Check this documentation first
2. Review the Supabase documentation
3. Check the browser console for errors
4. Test with a fresh user account

Happy coding! 🚀
