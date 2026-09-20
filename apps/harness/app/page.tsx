import { WorkbenchShell } from "@/components/WorkbenchShell";
import { HarnessApp } from "@/components/HarnessApp";

export default function Home() {
  return <WorkbenchShell active="cluster"><HarnessApp /></WorkbenchShell>;
}
