export default function SearchFilterContainer({ children, onSubmit }) {
  return <form className="card card-body mb-4" onSubmit={onSubmit}>{children}</form>;
}
