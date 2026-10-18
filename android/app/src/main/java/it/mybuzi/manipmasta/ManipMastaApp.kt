package it.mybuzi.manipmasta

import android.app.Application

class ManipMastaApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Notifications.ensureChannels(this)
    }
}
