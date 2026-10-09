plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val configuredApiBaseUrl = providers.gradleProperty("smartbusApiBaseUrl")
    .orElse(providers.environmentVariable("SMARTBUS_API_BASE_URL"))
    .orElse("https://replace-with-your-smartbus-domain.example/api/")
    .get()

android {
    namespace = "com.smartbus.driver"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.smartbus.driver"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        buildConfigField("String", "API_BASE_URL", "\"$configuredApiBaseUrl\"")
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
}
