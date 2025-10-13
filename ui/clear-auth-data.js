// Clear Authentication Data Script
// Run this in browser console to clear all authentication data

console.log('🧹 Clearing authentication data...');

// Clear localStorage
localStorage.clear();
console.log('✅ Cleared localStorage');

// Clear sessionStorage  
sessionStorage.clear();
console.log('✅ Cleared sessionStorage');

// Clear NextAuth cookies
document.cookie.split(";").forEach(function(c) { 
    document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
});
console.log('✅ Cleared cookies');

// Clear any tenant context
if (typeof window !== 'undefined') {
    // Clear any cached tenant data
    delete window.__TENANT_CONTEXT__;
    delete window.__AUTH_DATA__;
}

console.log('🎉 All authentication data cleared!');
console.log('📝 Next steps:');
console.log('1. Go to http://company1.localhost:3000/sign-in');
console.log('2. Login with your company1 credentials');
console.log('3. You should now have access to the correct tenant');
