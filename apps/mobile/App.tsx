import React from 'react';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {GestureHandlerRootView} from 'react-native-gesture-handler';
import {SafeAreaProvider} from 'react-native-safe-area-context';
import {RootNavigator} from '@/navigation/RootNavigator';

const queryClient = new QueryClient();

export default function App() {
  return (
    <GestureHandlerRootView style={{flex: 1}}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <RootNavigator />
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
