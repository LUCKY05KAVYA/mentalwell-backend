import com.google.auth.oauth2.GoogleCredentials;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.io.FileInputStream;

@Component
public class FirebaseInitializer {
    @PostConstruct
    public void init() {
        try {
            FileInputStream serviceAccount = new FileInputStream("src/main/resources/firebase-key.json");

            FirebaseOptions options = new FirebaseOptions.Builder()
                    .setCredentials(GoogleCredentials.fromStream(serviceAccount))
                    .build();

            if (FirebaseApp.getApps().isEmpty()) {
                FirebaseApp.initializeApp(options);
            }

            System.out.println("✅ Firebase Initialized");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
