// firebase.js
const admin = require('firebase-admin');
const serviceAccount = require('./firebase-adminsdk.json'); // your downloaded file

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  databaseURL: 'https://mentalwell-64a8b-default-rtdb.firebaseio.com', // Replace with your Firebase Realtime DB URL
});

module.exports = admin;
