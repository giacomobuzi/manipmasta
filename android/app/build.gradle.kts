plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Firma release opzionale: attiva solo se la CI (o l'utente) esporta MM_KEYSTORE_FILE.
// Senza keystore assembleRelease produce app-release-unsigned.apk (non installabile così com'è).
val ksPath: String = System.getenv("MM_KEYSTORE_FILE") ?: ""
val hasKeystore: Boolean = ksPath.isNotBlank()

android {
    namespace = "it.mybuzi.manipmasta"
    compileSdk = 35

    defaultConfig {
        applicationId = "it.mybuzi.manipmasta"
        minSdk = 26
        targetSdk = 35
        versionCode = System.getenv("MM_VERSION_CODE")?.toIntOrNull() ?: 1
        versionName = System.getenv("MM_VERSION_NAME") ?: "1.0.0"
    }

    signingConfigs {
        if (hasKeystore) {
            create("release") {
                storeFile = file(ksPath)
                storePassword = System.getenv("MM_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("MM_KEY_ALIAS")
                keyPassword = System.getenv("MM_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            if (hasKeystore) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        buildConfig = true
    }

    lint {
        // Evita che lintVitalRelease blocchi la build in CI; lanciare `gradle lint` a parte.
        checkReleaseBuilds = false
        abortOnError = false
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")
    implementation("androidx.preference:preference-ktx:1.2.1")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
}
