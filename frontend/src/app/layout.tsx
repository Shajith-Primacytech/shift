import type { Metadata } from "next";
import { KnowledgeProvider } from "@/components/knowledge-provider";
import { AppShell } from "@/components/app-shell";
import "./globals.css";
export const metadata: Metadata = {
  title: "SHIFT — Industrial Knowledge Intelligence",
  description:
    "The Memory of the Factory Floor. Synthetic demonstration workspace.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <KnowledgeProvider>
          <AppShell>{children}</AppShell>
        </KnowledgeProvider>
      </body>
    </html>
  );
}
