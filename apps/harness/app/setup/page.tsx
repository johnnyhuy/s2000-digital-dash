import { WorkbenchShell } from "@/components/WorkbenchShell";
import SetupViewer from "@/components/SetupViewer";

export default function Setup() {
  return <WorkbenchShell active="setup"><SetupViewer /></WorkbenchShell>;
}
