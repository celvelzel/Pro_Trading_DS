import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from "sonner";
import { QueryProvider } from "@/providers/QueryProvider";
import { ThemeProvider } from "@/components/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { GlobalErrorBoundary } from "@/components/GlobalErrorBoundary";
import { KeyboardShortcutsProvider } from "@/components/KeyboardShortcutsProvider";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { MobileNav } from "@/components/layout/MobileNav";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Lobster Quant - Professional Trading Analysis",
  description: "Quantitative trading analysis platform with real-time market data, technical indicators, and strategy backtesting.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex bg-background text-foreground" suppressHydrationWarning>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <QueryProvider>
            <TooltipProvider>
              <GlobalErrorBoundary>
                <KeyboardShortcutsProvider>
                  {/* Sidebar - hidden on mobile */}
                  <Sidebar />
                  
                  {/* Main content area */}
                  <div className="flex-1 flex flex-col min-h-screen">
                    {/* Header */}
                    <Header />
                    
                    {/* Page content */}
                    <main className="flex-1 overflow-auto">
                      {children}
                    </main>
                    
                    {/* Mobile navigation - visible only on mobile */}
                    <MobileNav />
                  </div>
                </KeyboardShortcutsProvider>
              </GlobalErrorBoundary>
            </TooltipProvider>
          </QueryProvider>
          <Toaster richColors position="top-right" />
        </ThemeProvider>
      </body>
    </html>
  );
}
