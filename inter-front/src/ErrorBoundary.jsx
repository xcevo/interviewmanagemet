import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(p){ super(p); this.state = { hasError: false }; }
  static getDerivedStateFromError(){ return { hasError: true }; }
  componentDidCatch(error, info){
    console.group("%cRender error caught","font-weight:bold");
    console.error(error);
    console.log("Component stack:\n", info.componentStack);
    console.groupEnd();
  }
  render(){
    if (this.state.hasError) return <div style={{padding:12}}>Render error – console dekho.</div>;
    return this.props.children;
  }
}
