import './globals.css';
import { AuthProvider } from '@/context/AuthContext';

export const metadata = {
  title: 'HostingSignal - Web Hosting Control Panel',
  description: 'Modern web hosting control panel with license distribution. Manage websites, domains, emails, databases, and more.',
  keywords: 'web hosting, control panel, hosting management, license distribution',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
