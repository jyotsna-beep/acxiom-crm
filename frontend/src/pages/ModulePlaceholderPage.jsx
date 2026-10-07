import EmptyState from "../components/common/EmptyState";
import PageHeader from "../components/common/PageHeader";

export default function ModulePlaceholderPage({ title }) {
  return <><PageHeader title={title} description="This module is available in a later phase." /><EmptyState title={`${title} not implemented yet`} message="The application shell and route protection are ready." /></>;
}
