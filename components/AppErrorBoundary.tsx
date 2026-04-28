import type { PropsWithChildren } from "react";
import { Component } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

type AppErrorBoundaryProps = PropsWithChildren<{
  onReset?: () => void;
}>;

type AppErrorBoundaryState = {
  hasError: boolean;
  errorMessage: string;
};

export class AppErrorBoundary extends Component<
  AppErrorBoundaryProps,
  AppErrorBoundaryState
> {
  public state: AppErrorBoundaryState = {
    hasError: false,
    errorMessage: "",
  };

  public static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return {
      hasError: true,
      errorMessage: error.message,
    };
  }

  public componentDidCatch(error: Error): void {
    console.error("[AppErrorBoundary] Unexpected render crash", error);
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, errorMessage: "" });
    this.props.onReset?.();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <View style={styles.container}>
          <Text style={styles.title}>The app hit an unexpected issue</Text>
          <Text style={styles.message}>{this.state.errorMessage || "Unknown error"}</Text>
          <Pressable onPress={this.handleReset} style={styles.button}>
            <Text style={styles.buttonText}>Restart App</Text>
          </Pressable>
        </View>
      );
    }

    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f8f3eb",
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
    gap: 14,
  },
  title: {
    fontSize: 22,
    fontWeight: "800",
    color: "#13293d",
    textAlign: "center",
  },
  message: {
    fontSize: 14,
    color: "#36414d",
    textAlign: "center",
    lineHeight: 20,
  },
  button: {
    backgroundColor: "#13293d",
    borderRadius: 14,
    paddingHorizontal: 20,
    paddingVertical: 10,
  },
  buttonText: {
    color: "#f7f4ef",
    fontSize: 14,
    fontWeight: "700",
  },
});
