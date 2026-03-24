package com.apkeditor.app;

import android.content.Context;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintJob;
import android.print.PrintManager;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.os.Bundle;

import androidx.annotation.NonNull;

import io.flutter.embedding.android.FlutterActivity;
import io.flutter.embedding.engine.FlutterEngine;
import io.flutter.plugin.common.MethodChannel;

/**
 * MainActivity + PrintBridge
 * ──────────────────────────
 * Registers a Flutter/Flet MethodChannel named "com.apkeditor.app/print".
 *
 * Flet Python side calls:
 *   page.invoke_method("print_html", {"html": "<html>...</html>", "job_name": "Fatura"})
 *
 * This class receives the call and invokes Android's PrintManager,
 * which shows the system print dialog (supports PDF save, Wi-Fi printers,
 * Bluetooth printers, Google Cloud Print, etc.).
 */
public class MainActivity extends FlutterActivity {

    private static final String PRINT_CHANNEL = "com.apkeditor.app/print";

    @Override
    public void configureFlutterEngine(@NonNull FlutterEngine flutterEngine) {
        super.configureFlutterEngine(flutterEngine);

        new MethodChannel(
                flutterEngine.getDartExecutor().getBinaryMessenger(),
                PRINT_CHANNEL
        ).setMethodCallHandler((call, result) -> {

            if ("print_html".equals(call.method)) {
                String html    = call.argument("html");
                String jobName = call.argument("job_name");
                if (html == null) {
                    result.error("MISSING_HTML", "html argument is null", null);
                    return;
                }
                printHtml(html, jobName != null ? jobName : "APK Editor Print Job");
                result.success(null);

            } else {
                result.notImplemented();
            }
        });
    }

    // ─────────────────────────────────────────────────────────────────────
    // Android Print via WebView
    // ─────────────────────────────────────────────────────────────────────

    /**
     * Loads the HTML into an off-screen WebView, then triggers the system
     * print dialog via PrintManager.createPrintJob().
     */
    private void printHtml(String html, String jobName) {
        // Off-screen WebView – never added to view hierarchy
        WebView webView = new WebView(this);
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return false;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                // Page is fully rendered – create the print adapter
                PrintDocumentAdapter printAdapter =
                        view.createPrintDocumentAdapter(jobName);

                PrintManager printManager =
                        (PrintManager) getSystemService(Context.PRINT_SERVICE);

                if (printManager == null) return;

                PrintAttributes.Builder attrBuilder = new PrintAttributes.Builder();
                attrBuilder.setMediaSize(PrintAttributes.MediaSize.ISO_A4);
                attrBuilder.setResolution(
                        new PrintAttributes.Resolution("pdf", "PDF", 600, 600));
                attrBuilder.setMinMargins(PrintAttributes.Margins.NO_MARGINS);

                PrintJob printJob = printManager.print(
                        jobName,
                        printAdapter,
                        attrBuilder.build()
                );
                // printJob object can be stored to query status later
            }
        });

        // Enable JavaScript (required for the print button inside the HTML)
        webView.getSettings().setJavaScriptEnabled(true);
        webView.loadDataWithBaseURL(
                null,
                html,
                "text/html",
                "UTF-8",
                null
        );
    }
}
