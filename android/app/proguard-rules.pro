# proguard-rules.pro
# Keep Flutter/Flet engine
-keep class io.flutter.** { *; }
-keep class io.flutter.embedding.** { *; }

# Keep our MainActivity (PrintBridge)
-keep class com.apkeditor.app.MainActivity { *; }

# Keep FileProvider
-keep class androidx.core.content.FileProvider { *; }

# Keep print adapter
-keep class android.print.** { *; }
-keep class android.webkit.WebView { *; }
-keep class android.webkit.WebViewClient { *; }

# Prevent stripping of method channel handlers
-keepclassmembers class * {
    @io.flutter.plugin.common.MethodChannel.* <methods>;
}
