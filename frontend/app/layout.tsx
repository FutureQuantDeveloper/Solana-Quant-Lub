import type {Metadata} from "next";
import {WorkspaceProvider} from "@/components/workspace";
import "./globals.css";
export const metadata:Metadata={title:"Solana Quant Research Lab",description:"Reproducible on-chain factor research, event-driven backtesting and chronological validation."};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body><WorkspaceProvider>{children}</WorkspaceProvider></body></html>;}
